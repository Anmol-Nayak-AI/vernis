# Vernis evaluations

Only reproducible, truthfully labeled evaluation material belongs here. The current fixture is generated synthetic data and tests implementation behavior; it is not evidence of accuracy on artwork, conservation, rights, or valuation data.

Run the computer-vision smoke evaluation through `POST /api/v1/organizations/{organization_id}/forensics/evaluations`, and run the local latency smoke measurement with:

```bash
cd backend
uv run python -m scripts.performance_smoke
```

Domain release gates remain blocked until licensed, representative fixtures and expert-authored labels are available. Never add customer artwork or confidential evidence without documented consent and retention controls.
