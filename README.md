# Vernis — Art Intelligence Platform

Vernis is trust and commerce infrastructure for AI-assisted art. It helps artists and galleries move from an art-directed image to a professionally reviewed, evidence-backed cultural object with a living authorship, rights, provenance, edition, and ownership record.

## Product surface

- **AI Atelier:** 36 material-aware art directions, automatic direction, style blending, palette intent, originality control, 4 aspect ratios, 4 quality tiers, and resumable background renders with up to 4 variants.
- **Art discovery:** public-domain masterworks from the Art Institute of Chicago API, an artist index, and original visual-language studies.
- **Commerce:** fixed-price listings, digital-collectible-ready records, timed auction models, bid history, editions, USD pricing, and international settlement controls.
- **Trust:** SHA-256 master fingerprints, downloadable artwork passports, evidence-completeness controls, provenance events, rights declarations, immutable-style audit records, and separation of public previews from private masters.
- **Enterprise workspace:** owner/admin/curator/artist/finance/viewer roles, private collections, team surfaces, usage records, and billing status.
- **Immersive interface:** Motion page transitions and a lazily loaded React Three Fiber gallery object.
- **Vernis Art Council:** separate curator, provenance/rights, and market-strategy agents synthesize a human-review dossier. CrewAI is the preferred orchestrator; a native OpenAI agent council keeps local development functional when CrewAI is unavailable.

## Architecture

```text
React + Vite + Motion
             │
             ├── Supabase Auth + Postgres/RLS (identity, studio, commerce, provenance)
             ├── FastAPI (token verification, background generation jobs, billing, advisory)
             ├── OpenAI image generation (primary/fallback models)
             ├── Stripe hosted Checkout (credential-gated)
             └── CrewAI council or native OpenAI agent orchestration
```

The browser only receives Supabase publishable credentials. Supabase service-role keys, Stripe secrets, and provider keys must remain server-side. Every table exposed through Supabase has row-level security enabled in the included migration.

## Run locally

Use Python 3.10–3.13 and Node 22.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY. Supabase and Stripe can remain disabled for UI evaluation.
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/generated` to FastAPI.

## Enable authentication and cloud persistence

1. Create a Supabase project.
2. Apply [`supabase/migrations/20261022145558_enterprise_art_platform.sql`](supabase/migrations/20261022145558_enterprise_art_platform.sql) using `npx supabase db push` from a linked project.
3. Put `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` in `frontend/.env.local`.
4. Put the same `SUPABASE_URL` in `backend/.env` and set `AUTH_REQUIRED=true` for production.
5. Configure the desired sign-in providers and exact redirect URLs in Supabase Auth.

On first authenticated use, the client creates the user's profile, private workspace, and owner membership through RLS-protected inserts. Generated artwork records then persist to the workspace archive.

## Enable Stripe billing

Create recurring prices in Stripe and set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_CREATOR`, `STRIPE_PRICE_STUDIO`, and `STRIPE_PRICE_ENTERPRISE` in `backend/.env`. Checkout uses Stripe's hosted page; Vernis never handles raw card data. A production launch should add webhook-driven entitlement reconciliation before access is granted from a payment event.

## Enable CrewAI advisory

CrewAI currently requires Python 3.10+. Install the optional bundle and enable it explicitly:

```bash
cd backend
pip install -r requirements-agents.txt
# in .env
CREW_ENABLED=true
CREW_MODEL=gpt-4o-mini
```

`POST /api/advisory/analyze` runs sequential curator, rights/provenance, and market agents, followed by a chief dossier editor. Without CrewAI, the endpoint automatically uses the native OpenAI agent council. Output is informational and must not be treated as legal, tax, investment, valuation, or authenticity certification.

## API surface

- `GET /api/studio/styles`
- `POST /api/studio/jobs` — starts a resumable render and returns immediately
- `GET /api/studio/jobs/{job_id}` — polls queued, running, succeeded, and failed states
- `POST /api/studio/generate` — synchronous compatibility endpoint
- `POST /api/billing/checkout` — authenticated and credential-gated
- `POST /api/advisory/analyze` — multi-agent artwork dossier; auth follows the server's `AUTH_REQUIRED` policy
- `GET /api/platform/capabilities`
- `POST /api/compare` — retained architecture diagnostic

## Verification

```bash
cd frontend && npm run build && npm audit --omit=dev
cd ../backend && python3 -m compileall -q app
curl http://127.0.0.1:8000/api/platform/capabilities
```

Generated images are written to `backend/generated` for local development and their SHA-256 fingerprint is included in the generation response. The browser preserves a local studio archive and can export a portable JSON artwork passport. Local background jobs survive browser navigation but remain process-local. Production should move private masters and passport evidence to signed object-storage URLs, replace the in-process runner with a durable queue (for example Redis plus workers), add rate limits, configure Stripe webhooks and tax rules, perform jurisdiction-specific KYC/AML review, and deploy observability and backups before accepting real money.
