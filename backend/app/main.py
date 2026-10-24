import hashlib
import json
import logging
import time
import uuid
from threading import Lock
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.config import settings
from app.auth import AuthPrincipal, get_current_user, require_user
from app.schemas import GenerateRequest, GenerateResponse
from app.services.image_service import ImageGenerationError, generate_artwork
from app.services.billing_service import create_checkout_session
from app.services.curator_crew import run_art_advisory
from app.style_catalog import ART_STYLES, public_style_catalog
from app.api.v1 import router as api_v1_router
from app.api.v1.forensics import router as forensics_router
from app.api.v1.engines import router as engines_router
from app.api.v1.billing import router as billing_router
from app.core.observability import metrics
from app.core.rate_limit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.mount("/generated", StaticFiles(directory=settings.generated_assets_dir, check_dir=False), name="generated")
app.include_router(api_v1_router)
app.include_router(forensics_router)
app.include_router(engines_router)
app.include_router(billing_router)

generation_jobs: dict[str, dict[str, Any]] = {}
generation_jobs_lock = Lock()


@app.exception_handler(HTTPException)
async def versioned_http_error(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/v1/"):
        return await http_exception_handler(request, exc)
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def versioned_validation_error(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/v1/"):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "request_id": getattr(request.state, "request_id", None),
                "fields": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
    request.state.request_id = request_id
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    route = getattr(request.scope.get("route"), "path", request.url.path)
    metrics.observe(request.method, route, response.status_code, duration_ms)
    logging.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )
    )
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
    response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["x-process-time-ms"] = f"{duration_ms:.1f}"
    return response


@app.get("/api/v1/metrics", response_class=PlainTextResponse, include_in_schema=False)
def prometheus_metrics() -> str:
    return metrics.prometheus()


class AgentRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(creator|studio|enterprise)$")


class AdvisoryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=10, max_length=4000)
    commercial_goal: str = Field(default="Responsible primary-market release", max_length=1000)


def _run_generation_job(job_id: str, request: GenerateRequest) -> None:
    with generation_jobs_lock:
        generation_jobs[job_id]["status"] = "running"
        generation_jobs[job_id]["started_at"] = time.time()
    try:
        result = generate_artwork(request)
        with generation_jobs_lock:
            generation_jobs[job_id].update(status="succeeded", result=result.model_dump(), completed_at=time.time())
    except Exception as exc:
        logging.exception("Background image generation failed")
        detail = str(exc) if isinstance(exc, (ValueError, ImageGenerationError)) else "Unexpected generation failure. Please retry."
        with generation_jobs_lock:
            generation_jobs[job_id].update(status="failed", error=detail, completed_at=time.time())


@app.post("/api/studio/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    principal: AuthPrincipal = Depends(get_current_user),
):
    if principal.user_id:
        request.safety_identifier = hashlib.sha256(principal.user_id.encode("utf-8")).hexdigest()
    job_id = uuid.uuid4().hex
    with generation_jobs_lock:
        # Bound process memory while keeping recent jobs resumable.
        if len(generation_jobs) >= 100:
            completed = [key for key, value in generation_jobs.items() if value["status"] in {"succeeded", "failed"}]
            if completed:
                oldest = min(completed, key=lambda key: generation_jobs[key]["created_at"])
                generation_jobs.pop(oldest, None)
        generation_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "user_id": principal.user_id,
            "created_at": time.time(),
        }
    background_tasks.add_task(_run_generation_job, job_id, request)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/studio/jobs/{job_id}")
def get_generation_job(job_id: str, principal: AuthPrincipal = Depends(get_current_user)):
    with generation_jobs_lock:
        job = generation_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Generation job was not found or has expired.")
        if job["user_id"] and job["user_id"] != principal.user_id:
            raise HTTPException(status_code=403, detail="You do not have access to this generation job.")
        return dict(job)


@app.get("/api/studio/styles")
def list_styles():
    return {"styles": public_style_catalog(), "count": len(ART_STYLES)}


@app.post("/api/studio/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, principal: AuthPrincipal = Depends(get_current_user)):
    try:
        if principal.user_id:
            request.safety_identifier = hashlib.sha256(principal.user_id.encode("utf-8")).hexdigest()
        return await run_in_threadpool(generate_artwork, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        logging.exception("Unexpected image generation error")
        return JSONResponse(status_code=500, content={"detail": "Unexpected generation failure. Please retry."})


@app.post("/api/billing/checkout")
async def billing_checkout(request: CheckoutRequest, principal: AuthPrincipal = Depends(require_user)):
    return await run_in_threadpool(create_checkout_session, request.plan, principal)


@app.post("/api/advisory/analyze")
async def advisory(request: AdvisoryRequest, _: AuthPrincipal = Depends(get_current_user)):
    report = await run_in_threadpool(run_art_advisory, request.title, request.description, request.commercial_goal)
    return {**report, "disclaimer": "AI-assisted review for human consideration. Not authentication, appraisal, legal, tax, or investment advice."}


@app.get("/api/platform/capabilities")
def capabilities():
    return {
        "authentication": bool(settings.supabase_url),
        "authentication_required": settings.auth_required,
        "billing": bool(settings.stripe_secret_key),
        "art_advisory": bool(settings.openai_api_key),
        "art_advisory_crew": settings.crew_enabled,
        "art_advisory_engine": "CrewAI" if settings.crew_enabled else "Vernis native agent council",
        "image_generation": bool(settings.openai_api_key),
    }


# Kept for architecture demos. The studio endpoint above is the production path
# and deliberately performs exactly one image-generation workflow per request.
@app.post("/api/compare")
def compare_execution(req: AgentRequest):
    # Lazy imports keep optional architecture-demo dependencies out of the
    # production studio startup path.
    from app.engines.langchain_runner import execute_langchain_agent
    from app.engines.langgraph_runner import execute_langgraph_agent

    return {
        "langchain": execute_langchain_agent(req.prompt),
        "langgraph": execute_langgraph_agent(req.prompt),
    }


@app.get("/")
def root():
    return {"status": "ok", "service": settings.app_name, "version": "2.0.0"}
