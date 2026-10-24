from celery import Celery

from app.config import settings

celery_app = Celery("vernis", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="vernis.health.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@celery_app.task(
    name="vernis.engine.run",
    autoretry_for=(),
    acks_late=True,
)
def run_engine_case(agent_run_id: str) -> dict[str, str]:
    import uuid

    from app.services.investigation_crew import execute_engine_crew

    execute_engine_crew(uuid.UUID(agent_run_id))
    return {"agent_run_id": agent_run_id, "status": "completed"}
