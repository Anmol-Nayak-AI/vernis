# Engineering decisions

- Alembic owns application DDL. Supabase is used for Auth/Postgres/RLS compatibility; duplicating all tables into Supabase migrations would create two authorities.
- The `vernis` schema and additive migrations preserve legacy `public` data and `/legacy` routes during cutover.
- FastAPI authorization plus forced RLS provides two independent tenant checks.
- Local/S3 storage share one interface; local signed tokens enable inexpensive development while production rejects local storage.
- The first CV descriptor is small, deterministic, CPU-friendly, and explicitly limited. It establishes the inference/version/evaluation contract before licensed domain models exist.
- Private feature-hash text vectors avoid sending evidence to an embedding provider. Their lexical nature is disclosed.
- Engine domain state uses relational tables with explicit provenance instead of prematurely adding a graph database.
- CrewAI runs only after explicit consent, receives scoped tools, and cannot make the final professional decision.
- Reports and passports are versioned snapshots so later changes do not rewrite prior evidence packages.
- Stripe webhooks are the billing reconciliation authority; UI redirects are not.
