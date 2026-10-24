# Engineering walkthrough

Use this sequence to explain Vernis:

1. Start with the non-negotiable boundary: the system organizes and computes evidence; humans decide authenticity, infringement, treatment, certified value, and liability.
2. Show the canonical artwork and how all six cases reuse it.
3. Trace an upload through single-use intake, secure decode, SHA-256, private storage, and tenant-scoped visual analysis.
4. Trace an evidence record through OCR, chunks, hybrid retrieval, claim citation, CrewAI validation, human review, report, and passport.
5. Explain API RBAC plus database RLS using the cross-tenant test.
6. Discuss why the deterministic CV/text baselines are useful infrastructure but not domain models.
7. Demonstrate subscription enforcement, idempotent webhooks, usage events, metrics, backup, and scratch restore.

Likely tradeoff questions: why PostgreSQL instead of a graph/vector database; why local descriptors before OpenCLIP; why synchronous OCR but asynchronous agents; how prompt injection is bounded; how public passport data differs from internal data; how migrations preserve legacy state; and what evidence would be required before calling the platform production-ready.

The strongest answer to an unimplemented provider/model question is the honest one: the interface, authorization, persistence, and unavailable state exist, but a licensed dataset/provider and measured validation are still required.
