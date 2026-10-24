# CrewAI architecture

Vernis defines a separate narrow CrewAI team for every engine: 6 ArtSentinel agents, 5 ArtShield agents, 5 ConservaVision agents, 6 MuseGraph agents, 6 ArtValuate agents, and 5 ArtTransit agents. Each team ends in a structured Pydantic dossier.

```mermaid
sequenceDiagram
  participant U as User
  participant A as API
  participant Q as Redis/Celery
  participant C as CrewAI
  participant T as Tenant tools
  participant R as Human reviewer
  U->>A: Start run + explicit consent
  A->>Q: Queue scoped case/run IDs
  Q->>C: Execute bounded sequential crew
  C->>T: Typed artwork/evidence/visual/case lookup
  T-->>C: Authorized records + source IDs
  C-->>A: Validated dossier + usage/errors
  A->>A: Reject invalid citations / partial status
  R->>A: Approve, reject, or request changes
```

Tools never receive unrestricted SQL or a user-selected organization. They are constructed with server-authorized organization, case, and run IDs. Evidence text is explicitly untrusted and cannot act as tool instruction. Agents have no delegation, use bounded iterations, preserve tool events, and do not store chain-of-thought.

External execution is disabled unless server configuration, an API key, and per-run consent all agree. Current external runs send authorized text/metadata and deterministic visual findings, not image bytes. A provider outage records a failed job without inventing a dossier. Human review remains mandatory.
