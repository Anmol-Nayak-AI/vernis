# API design

New APIs live under `/api/v1`. Organization-owned resources use `/organizations/{organization_id}/...`; authentication resolves a principal and every handler verifies membership and role. Errors use `{ "error": { "code", "message", "request_id" } }`. UUIDs are stable identifiers and timestamps are UTC ISO 8601.

Core resources cover organizations, artworks, upload intents/assets, command-center metrics, forensic analysis/comparison/models/evaluations, cases for all six engines, evidence/OCR/search, claims, provenance, reviews, reports, agent runs, passports, billing, entitlements, and usage.

Mutating routes emit audit events where decisions or sensitive artifacts change. Upload URLs are time-limited and single-use; download URLs expire. Collection lists are bounded, and artwork lists are paginated. Agent creation requires explicit external-AI consent and returns `202` with job/run IDs. Report and passport exports are immutable versions.

Interactive OpenAPI is available from FastAPI in development. Clients must not interpret `awaiting_review` as approval, visual similarity as a legal finding, or a research valuation as a certified appraisal.
