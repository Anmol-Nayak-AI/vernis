# Evidence graph

The initial evidence graph uses explicit relational edges rather than a separate graph database. Artwork, evidence, claims, provenance events, collection relationships, shipments, custody events, cases, and reviews retain stable IDs and source references.

```mermaid
graph TD
  E[Evidence document] -->|supports / contradicts / context| C[Claim]
  C --> K[Engine case]
  K --> A[Artwork]
  E --> P[Provenance assertion]
  P --> A
  A --> CR[Collection record]
  CR -->|unverified/reviewed/verified| CR2[Related record]
  A --> S[Shipment]
  S --> CE[Custody event]
  K --> HR[Human review]
```

Extraction never promotes text to historical truth. Provenance begins as `asserted`; collection relationships begin `unverified`; claims carry stance and review status. Public passport exports include approved workflow summaries and public evidence only. Internal exports additionally require a privileged role.
