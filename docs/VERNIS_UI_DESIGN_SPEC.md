# VERNIS UI Design Specification

Status: Phase 0 design proposal — no application UI has been changed

Creative direction: **Contemporary art museum × luxury editorial × advanced research laboratory**

## 1. Experience principles

1. **The artwork is the primary object.** Interfaces frame the work; they do not compete with it.
2. **Evidence before assertion.** Every consequential finding exposes source, method, status, uncertainty, and reviewer state.
3. **Editorial calm, scientific precision.** Generous space and refined typography coexist with dense, structured forensic tools.
4. **Progressive disclosure.** Executive summaries lead to regions, parameters, citations, and raw evidence without forcing every user into expert detail.
5. **No theatrical falsehoods.** Animated progress reflects real job state. Metrics, sales, findings, and agent activity come from APIs or are explicitly labeled demo fixtures.
6. **Human authority remains visible.** AI observations and human decisions have distinct visual treatments and immutable attribution.

## 2. Brand identity

### 2.1 Positioning

**VERNIS — The Art Intelligence Operating System**

Primary promise: an evidence-centered operating environment for artwork investigation, intellectual-property protection, conservation, valuation research, collection intelligence, and transport/insurance documentation.

Voice is precise, cultured, calm, and candid. Prefer “observable change,” “potential match,” “claimed attribution,” “supporting evidence,” and “requires review.” Avoid “certified authentic,” “forgery detected,” “copyright theft confirmed,” “guaranteed value,” or “claim approved.”

### 2.2 Mark and wordmark

- Primary wordmark: `VERNIS` in spaced capitals, paired with a small “Art Intelligence OS” descriptor.
- The existing multicolor seal may inform an animated loading/identity motif, but the production mark should be simplified to a reproducible one-color `V` aperture/seal.
- Use the mark sparingly: navigation, authentication, export cover, and loading state. Never watermark uploaded artwork.

### 2.3 Imagery policy

- Authenticated product views prioritize user-authorized artwork.
- Public marketing uses licensed, public-domain, or commissioned imagery with source/license metadata.
- Each bundled public image requires `source`, `creator`, `license`, `license_url`, and `attribution_text` in a manifest.
- Generic gradients may support empty states, but cannot masquerade as artwork, evidence, damage maps, or market data.
- Existing bundled images are quarantined until provenance is documented.

## 3. Typography

Preferred family pair:

- Editorial/display: **Fraunces**, variable optical-size cut, SIL Open Font License.
- Interface/text: **DM Sans**, SIL Open Font License.
- Data/identifiers: **DM Mono**, SIL Open Font License.

These preserve the strongest part of the current visual identity. Production builds should self-host subset WOFF2 files and include license files instead of depending on runtime Google Fonts.

Type scale:

| Token | Desktop | Mobile | Use |
| --- | --- | --- | --- |
| `display-2xl` | 72/0.94 | 48/0.98 | Public hero only |
| `display-xl` | 56/0.98 | 40/1.00 | Module/page statement |
| `heading-lg` | 36/1.05 | 30/1.08 | Workspace title |
| `heading-md` | 24/1.15 | 22/1.18 | Major panel |
| `heading-sm` | 18/1.25 | 18/1.25 | Cards/dialogs |
| `body-lg` | 17/1.65 | 16/1.60 | Editorial lead |
| `body-md` | 15/1.55 | 15/1.55 | Default interface text |
| `body-sm` | 13/1.50 | 13/1.50 | Secondary metadata |
| `label` | 12/1.25 | 12/1.25 | Controls/status labels |
| `mono` | 12/1.45 | 12/1.45 | IDs, model versions, measurements |

No essential text may render below 12 px. Uppercase labels use modest tracking and short phrases. Serif is not used for dense tables, form controls, or long technical copy.

## 4. Color system

### 4.1 Foundation tokens

| Token | Value | Role |
| --- | --- | --- |
| `charcoal-950` | `#0C0C0D` | primary dark canvas |
| `charcoal-900` | `#141416` | app shell |
| `charcoal-850` | `#1A1A1D` | raised surface |
| `charcoal-800` | `#232326` | hover/selected surface |
| `ivory-50` | `#F5F0E7` | light canvas / primary dark-theme text |
| `ivory-100` | `#EAE2D5` | secondary light surface |
| `stone-400` | `#A8A098` | muted text on dark |
| `stone-600` | `#68635F` | muted text on light |
| `bronze-500` | `#A97B47` | brand accent |
| `bronze-300` | `#D2AE78` | highlight/focus companion |
| `line-dark` | `rgba(245,240,231,.14)` | dark dividers |
| `line-light` | `rgba(27,25,23,.14)` | light dividers |

Default application theme is dark neutral because image comparison benefits from a controlled surround. Reading-heavy reports and documentation use an ivory paper surface. Users can choose dark/light/system; exported reports use the light palette.

### 4.2 Semantic tokens

- Positive/reviewed: `#5E8F76` with icon and text.
- Attention/pending: `#C49A58` with icon and text.
- Critical/contradiction: `#B85C54` with icon and text; never use red alone.
- Informational/system: `#6F82B7`.
- Unknown/not evaluated: `#77736F` with explicit “Not evaluated.”

### 4.3 Engine accents

Engine color appears in a 2–4 px rule, icon, chart series, and focus halo—not as a full-page theme.

| Engine | Accent | Visual metaphor |
| --- | --- | --- |
| ArtSentinel | `#B7864F` | archival bronze / examination light |
| ArtShield | `#92709E` | ultraviolet rights scan |
| ConservaVision | `#5F8E7B` | conservation green |
| ArtValuate | `#6179A5` | market slate blue |
| MuseGraph | `#A56B5C` | catalog terracotta |
| ArtTransit | `#B39A62` | crate brass / custody seal |

All text/background combinations must meet WCAG 2.2 AA. Charts use shape, pattern, labels, and data tables in addition to hue.

## 5. Materials and elevation

- Flat surfaces dominate; glass is limited to sticky controls over artwork and uses an opaque fallback.
- Corners: 2 px on editorial frames, 8 px on controls/cards, 999 px only for statuses/avatars.
- Borders carry hierarchy more often than shadows.
- Shadows are broad and low-contrast: artwork lightbox, modal, floating compare controls only.
- Texture may appear as a subtle CSS grain on marketing surfaces, never over diagnostic imagery or text.
- Focus ring: 2 px `bronze-300` plus 2 px offset, visible on every interactive element.

## 6. Layout principles

### 6.1 Grid

- Public pages: 12-column, max content width 1440 px, 24–40 px gutters, editorial asymmetry.
- Application: 248 px primary rail, fluid workspace, optional 320–400 px evidence inspector.
- Investigation studio: artwork/evidence stage receives at least 55% width; controls and findings occupy the remainder.
- Dense tables and graphs live inside bounded panels with persistent headers and alternative list/table views.
- Spacing follows an 8 px base with 4 px micro-step: 4, 8, 12, 16, 24, 32, 48, 64, 96.

### 6.2 Shell

Desktop shell:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Org switcher / Global search / Jobs / Help / Account           │
├───────────────┬─────────────────────────────────────────────────┤
│ VERNIS        │ Breadcrumbs + page actions                      │
│ Command       ├─────────────────────────────────────────────────┤
│ Artworks      │                                                 │
│ Engines       │               Route workspace                   │
│ Evidence      │                                                 │
│ Reports       │                                                 │
│ Admin         │                                                 │
└───────────────┴─────────────────────────────────────────────────┘
```

The rail groups durable concepts. The six engines live in one expandable “Intelligence engines” group and show organization entitlements without advertising locked features as active.

### 6.3 Page anatomy

Each authenticated page uses:

1. Breadcrumb and stable object ID.
2. Title, status, relevant engine, and one primary action.
3. Scope/permission/context line.
4. Main workspace.
5. Optional contextual inspector or activity drawer.
6. Real empty/loading/error/partial/freshness state.

## 7. Navigation architecture

### 7.1 Public routes

```text
/
/platform
/engines/art-sentinel
/engines/art-shield
/engines/conserva-vision
/engines/art-valuate
/engines/muse-graph
/engines/art-transit
/solutions/artists
/solutions/galleries
/solutions/auction-houses
/solutions/museums
/solutions/collectors-advisors
/solutions/conservators
/solutions/logistics-insurers
/technology
/trust
/pricing
/docs
/sign-in
/sign-up
```

Public engine pages explain inputs, workflow, outputs, limitations, and review gates. They do not show fabricated dashboards or case results.

### 7.2 Authenticated routes

```text
/app/:orgSlug/command
/app/:orgSlug/artworks
/app/:orgSlug/artworks/:artworkId
/app/:orgSlug/artworks/:artworkId/passport
/app/:orgSlug/sentinel/:caseId
/app/:orgSlug/shield/:caseId
/app/:orgSlug/conservation/:inspectionId
/app/:orgSlug/valuation/:reportId
/app/:orgSlug/collections/:collectionId
/app/:orgSlug/transit/:shipmentId
/app/:orgSlug/agents/:runId?
/app/:orgSlug/evidence
/app/:orgSlug/reports
/app/:orgSlug/settings/{general,members,roles,security,integrations}
/app/:orgSlug/billing
/app/:orgSlug/admin
```

Routes are deep-linkable, permission-aware, and restore query/filter state through URL parameters.

### 7.3 Global command palette

`⌘/Ctrl K` searches authorized artworks, evidence, cases, reports, collections, shipments, and commands. Results group by type and show organization scope. It never queries across organizations by default.

## 8. Motion guidelines

- Route fade/translate: 160–220 ms, 4–8 px, standard easing.
- Artwork reveal: 280–420 ms opacity plus clip; no scale that distorts examination.
- Inspector/card expansion: 180–240 ms.
- Graph layout transition: up to 450 ms with a “stabilize layout” control.
- Job progress uses real state transitions and indeterminate animation only when percent is unavailable.
- Comparison slider responds directly to pointer/keyboard without spring lag.
- Hover effects never move actionable targets more than 2 px.
- Avoid perpetual ambient animations outside a running job indicator.

Under `prefers-reduced-motion: reduce`, remove transforms, parallax, autoplay, animated graph layouts, and smooth scrolling; use instantaneous state changes or brief opacity under 100 ms. Motion is never required to understand status.

## 9. Core component system

### 9.1 Primitives

- Button: primary, secondary, quiet, danger, icon; 40 px default target, 44 px on touch.
- Input, textarea, select/combobox, date/range fields, dimension editor, uncertainty selector.
- Dialog, drawer, popover, tooltip, tabs, accordion, command menu, toast.
- Data table with column settings, keyboard navigation, pagination, export, and responsive card alternative.
- Status chip combining icon, label, and semantic color.
- Empty, loading, stale, partial, offline, access-denied, and error states.

### 9.2 Domain components

- `ArtworkTile`, `ArtworkIdentityHeader`, `ArtworkMetadataPanel`.
- `EvidenceCard`, `CitationChip`, `ClaimRow`, `ContradictionBanner`, `CompletenessMeter`.
- `DeepZoomViewer`, `CompareSlider`, `RegistrationOverlay`, `HeatmapOverlay`, `RegionAnnotationLayer`.
- `CaseTimeline`, `CustodyTimeline`, `ProvenanceGraph`, `CollectionGraph`.
- `JobStatusRail`, `AgentRunTimeline`, `ToolExecutionRow`, `HumanReviewGate`.
- `ModelBadge`, `InferenceLimitations`, `DataCoveragePanel`.
- `ReportPreview`, `ExportPolicyDialog`, `PassportSummary`.

Components always distinguish:

- user-supplied fact;
- extracted but unverified claim;
- model observation;
- external source record;
- human-reviewed decision.

## 10. Required page designs

### 10.1 Public homepage

Hero uses one licensed artwork at museum scale with the positioning statement and two actions: “Explore the platform” and “Start a workspace.” Below it, an interactive artwork lifecycle reveals how one upload can branch into six optional workflows. Trust language and limitations appear before pricing. No fake customer logos or metrics.

### 10.2 Platform overview and engine pages

The overview centers the unified registry/evidence/passport model. Each engine page includes a real input → processing → human review → evidence-backed output sequence, target customers, example UI fragments labeled illustrative, data requirements, and safety boundaries.

### 10.3 Solutions, technology/trust, pricing, documentation

- Solutions reorganize the same capabilities by user goal and permissions.
- Technology explains shared CV, RAG, CrewAI Flow, human review, and deployment/data handling without unverifiable performance claims.
- Trust presents security, privacy, provider data flows, retention, incident/contact channels, and model limitations.
- Pricing reads from plan configuration when available; otherwise labels tiers as proposed. Enterprise uses contact flow, not a fake checkout.
- Documentation has searchable API/product guides, version badges, code examples, and last-reviewed dates.

### 10.4 Sign in and sign up

Two-column editorial layout on desktop, single column on mobile. Forms show organization-aware invitation context, password rules, SSO options when enabled, privacy terms, recovery, and precise auth errors. No user authorization is inferred from editable profile metadata.

### 10.5 Command Center

Art-first executive surface:

- Top row: registered works, active cases/jobs, reviews awaiting this user, storage/quota.
- Module strip: copyright matches, condition alerts, collection completeness, active shipments.
- Main area: real activity/case timeline and review queue.
- Secondary: usage/cost chart and engine distribution.

Every metric links to the filtered record set that produces it. New organizations see a guided three-step onboarding state: create/import artwork, add evidence, start one optional workflow.

### 10.6 Artwork Registry

Gallery/table toggle, server pagination, saved filters, bulk import, and upload. Tiles show image, title, claimed artist, date precision, medium, evidence completeness, active cases, and permission status. Unknown values display “Unknown,” never guessed copy.

### 10.7 Artwork Detail

Large artwork at left; identity, dimensions, attribution state, custody, and actions at right. Lower tabs: Overview, Assets, Evidence, Provenance, Condition, Rights, Market, Collection, Transit, Activity. Engine launch cards state required inputs and entitlement. One artwork ID persists across all tabs.

### 10.8 ArtSentinel Investigation Studio

Three-pane workspace:

```text
┌──────────────────┬───────────────────────────┬───────────────────┐
│ Case stages      │ Deep zoom / compare       │ Findings          │
│ Inputs           │ overlays / correspondences│ Evidence/citations│
│ Agent progress   │                           │ Review state      │
└──────────────────┴───────────────────────────┴───────────────────┘
```

Stages: Intake, Visual analysis, Provenance, Historical context, Contradictions, Review, Dossier. The top status explicitly says “Due diligence — not an authenticity certificate.” Similarity scores are accompanied by method/version and cannot be promoted directly to authenticity verdicts.

### 10.9 ArtShield Monitoring Workspace

Protected-art grid, configured source coverage, match queue, and case status. Match review uses side-by-side/deep-zoom images, transformation summary, geometric correspondences, source snapshot, rights assertions, and reviewer classification: unrelated style similarity, related but authorized, near-duplicate, potential unauthorized reproduction, insufficient evidence. Legal action is never an in-product automatic outcome.

### 10.10 ConservaVision Analysis Studio

Inspection selector and registered before/after viewer dominate. Toggle normalized/raw view, alignment confidence, heatmap, annotated regions, and measurement table. Findings contain “visible in supplied photographs” language and photography limitations. Treatment recommendation controls route to a conservator review rather than issuing irreversible instructions.

### 10.11 ArtValuate Market Intelligence

Artwork facts and data coverage precede any estimate. Comparable table shows source/license, sale date, venue, medium, dimensions, condition/provenance notes, currency normalization, and inclusion reason. Charts include accessible tables. Scenarios show assumptions and uncertainty intervals. With inadequate evidence, replace estimate with “Insufficient market evidence” and actionable missing-data guidance.

### 10.12 MuseGraph Collection Explorer

Collection overview, import batch status, catalog completeness, duplicate-resolution queue, semantic search, and evidence/provenance graph. Graph nodes have a keyboard-accessible result list and filtering controls. Entity merges require a compare/review dialog showing source fields and reversibility.

### 10.13 ArtTransit Shipment Workspace

Shipment header, route/custody timeline, artwork/packaging manifest, checkpoint evidence, pre/arrival comparison, image-quality warnings, potential-change queue, document checklist, and claim-support report. Liability and claim approval are absent; a reviewer may confirm only the evidence finding/status.

### 10.14 Agent Operations Console

Queue and workflow overview with status, duration, retry count, model/provider, token/inference usage, estimated cost, approval gates, and errors. Run detail shows sanitized state changes and tool executions with evidence links. It explicitly omits hidden reasoning/chain-of-thought.

### 10.15 Evidence Library

Faceted list by artwork, case, type, source, date, verification, sensitivity, and retention. Preview shows immutable version, checksum, custody history, access policy, OCR status, claims supported/contradicted, and every consuming report. Delete actions honor retention/legal holds and require confirmation.

### 10.16 Reports

Report library with type, artwork, engine, version, review state, audience, generated date, and superseded status. Preview includes citations and limitations. Export dialog shows exactly what will be included/redacted for Internal, Counterparty, Insurer, or Public audiences.

### 10.17 Artwork Passport

Passport is a cross-engine summary, not an authenticity badge. Sections: Identity, Fingerprints, Rights Assertions, Provenance Claims, Investigations, Condition, Valuation References, Collection Links, Shipments, Human Reviews, Evidence Completeness, Schema/Version. Public export defaults to minimum disclosure and lists omitted confidential sections without revealing content.

### 10.18 Organization Settings

General information, members/invitations, roles/permissions, security/session settings, provider consent/data residency, integrations, retention, audit export. Permission changes show impacted users and require re-authentication for sensitive actions.

### 10.19 Billing and Usage

Current plan, entitlements, quota meters, invoices/provider portal, cost history, and usage detail derived from server records. Test mode is visually persistent. Upgrades create provider checkout but do not change entitlement UI until webhook reconciliation succeeds.

### 10.20 Administration

Owner/admin-only surfaces for policy configuration, data exports, audit log, API keys, model/provider allowlist, external sources, and organization lifecycle. Platform super-administration is a separate deployment/operator capability and is never inferred from organization admin.

## 11. Artwork viewing experience

Use OpenSeadragon or equivalent for tiled deep zoom where source resolution merits it. Viewer capabilities:

- fit, 1:1, zoom, pan, navigator, rotate where authorized;
- keyboard controls and textual coordinate/zoom readout;
- original/normalized toggle;
- RGB/luminance and optional channel views for supported analyses;
- region annotations with label, author/model, timestamp, status, and measurement;
- overlay opacity, blend modes, heatmap legend, and “hide all overlays”;
- asset/version selector and immutable source metadata;
- download only after permission check via signed URL.

Diagnostic overlays never permanently alter the source image. A screen-reader-accessible region table provides the same findings.

## 12. Investigation interface rules

- Each case has a persistent scope/status banner and owner/reviewer.
- Left-stage navigation cannot imply completion from visual position alone; every stage has real state.
- Findings use severity, confidence type, evidence count, method/version, limitations, and review status.
- “Confidence” distinguishes model probability, retrieval similarity, data completeness, and human assessment; these are not combined into one pseudo-scientific score.
- Contradictions receive equal prominence to supporting evidence.
- Generated prose citations open the exact evidence page/region where possible.
- Partial failures name the unavailable analysis and allow scoped retry.
- Human decisions require actor, timestamp, disposition, and optional/required rationale.

## 13. Data visualization

- Recharts handles trends/distributions with SVG semantics and adjacent data tables.
- Cytoscape handles provenance/evidence graphs with non-canvas textual alternatives, search, filters, focus management, and a reduced-motion layout.
- React Flow handles job/agent stage diagrams, not evidentiary truth graphs.
- Never use 3D charts, decorative gauges for uncertain scientific findings, or unlabeled dual axes.
- Tooltips are supplemental; all values are keyboard reachable and available in a table/download.

## 14. Accessibility rules

Target WCAG 2.2 AA.

- Semantic landmarks, single logical `h1`, ordered headings, native controls where possible.
- Full keyboard operation, no keyboard traps, visible focus, skip link, and focus restoration after dialogs/routes.
- 44×44 px touch targets; 40 px minimum pointer target in dense desktop tools with sufficient spacing.
- Text contrast 4.5:1; large text/UI component contrast 3:1.
- Status is never color-only. Images have useful alt text or empty alt when decorative.
- Deep zoom, graph, chart, comparison, and annotation tools have list/table alternatives.
- Live regions announce job/review changes without narrating every progress animation.
- Forms associate label, description, error, required state, and server response.
- Reduced motion, 200% zoom, reflow at 320 CSS px, forced colors, and screen readers are included in automated/manual acceptance.
- Timed sessions warn before expiry and allow extension where policy permits.

## 15. Responsive behavior

### Desktop ≥ 1280 px

Persistent rail, header, multi-pane investigation layouts, contextual inspector, dense tables.

### Laptop 1024–1279 px

Narrow rail/icons with labels on demand; inspector becomes collapsible drawer; two-pane investigation layout.

### Tablet 768–1023 px

Rail becomes navigation sheet; primary artwork viewer is full width; findings appear in tabs/drawer; tables prioritize essential columns.

### Mobile 320–767 px

Bottom navigation for Command, Artworks, Cases, Jobs, More. Complex workspaces become a deliberate sequence: Viewer → Findings → Evidence → Review. Comparison viewer supports a vertical slider and full-screen mode. Graphs default to searchable relationship lists. Sticky actions respect safe areas and do not cover artwork.

No capability is silently removed on mobile; difficult actions may be presented as sequential screens with clear context.

## 16. Content and state standards

- Date/time displays user timezone and preserves UTC in details/export.
- Money shows currency, source date, normalization method, and nominal/real basis where applicable.
- Unknown, disputed, approximate, inferred, and not evaluated are distinct values.
- Job states: queued, running, awaiting review, succeeded, partially succeeded, failed, cancelling, cancelled.
- Evidence states: unverified, corroborated, contradicted, human verified, superseded, inaccessible.
- Freshness appears on external data and generated reports.
- Destructive actions state object count, retention consequence, and recoverability.
- Demo fixtures display a persistent `DEMO DATA` treatment and never mix with organization records.

## 17. Frontend quality gates

- Storybook or an equivalent component workbench covers primitives and domain states.
- Vitest/Testing Library covers keyboard behavior, forms, error states, and data rendering.
- Playwright covers authentication, organization selection, artwork upload/registry, one engine case, review, and export.
- axe checks every route template; manual NVDA/VoiceOver passes cover viewer, graph alternative, and modal focus.
- Visual regression at 1440, 1024, 768, 390, and 320 px.
- Bundle budgets are route-specific; heavy graph/viewer libraries load only on relevant routes.
- Core Web Vitals are measured on the public homepage and registry with an explicit test environment.
- `prefers-reduced-motion`, high contrast/forced colors, offline/API failure, empty organizations, large text, and long localized content are test fixtures.

## 18. Phase 1 design deliverables

After approval, the first design implementation should include:

1. Token files and licensed/self-hosted font assets.
2. Public/app route shells and navigation.
3. Core primitives with accessibility tests.
4. Command Center real empty/loading/error states.
5. Artwork Registry gallery/table, filters, create form, and upload journey.
6. Artwork Detail overview/assets/evidence/activity tabs.
7. Organization switcher, member-aware actions, job status drawer, and audit-visible action feedback.
8. A responsive verification matrix and screenshots from real browser QA.

ArtSentinel-specific compare/graph/agent components begin in Phase 3, after the shared viewer/evidence primitives and backend contracts exist.
