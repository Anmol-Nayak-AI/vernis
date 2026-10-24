# Security and privacy

Vernis treats artwork images and documents as confidential intellectual property.

- Supabase-compatible JWT verification identifies users in hosted mode; local fixed identity is development-only.
- API RBAC and PostgreSQL forced RLS jointly enforce tenant isolation. Tenant-qualified foreign keys prevent cross-organization references.
- Uploads are size-limited, single-use, MIME-decoded, SHA-256 fingerprinted, private, and served with expiring access. S3 should enable encryption and versioning.
- Restricted evidence is role-gated. Internal passports require privileged roles; public exports omit sensitive evidence and unreviewed engine history.
- External AI requires server enablement plus per-run consent. Current Crew tools provide text/metadata and computed findings, not artwork image bytes. Provider retention/region terms must be reviewed before production.
- Stripe webhooks require signature verification and idempotent event IDs. Entitlements are enforced server-side.
- Redis-backed production rate limits, quotas, request IDs, structured logs, CSP, permissions policy, and Prometheus-format metrics are enabled.
- Agent tools are typed and tenant-scoped; retrieved text is treated as untrusted data. Invalid citations become unresolved.
- Secrets remain environment-only and must be supplied by a production secret manager. Never commit `.env`.

Residual risks include unintegrated malware scanning, absence of a domain adversarial corpus, local-storage suitability only for development, dependency vulnerabilities between scans, and unavailable hosted backup evidence. Threat-model review must be repeated when adding external discovery, market providers, or image-capable external models.

The 2026-10-23 Python audit reduced 52 findings to five advisories in CrewAI's transitive `chromadb` 1.5.9 dependency. The advisory feed published no fixed version. Vernis does not use ChromaDB for application retrieval or expose its server; PostgreSQL/pgvector is authoritative. CI explicitly allows only those named advisories and fails on new findings. Remove the exception immediately when CrewAI publishes a compatible fixed dependency.
