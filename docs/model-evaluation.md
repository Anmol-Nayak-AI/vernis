# Model evaluation and limitations

The repository contains a seeded synthetic smoke fixture and a CPU latency script under `evaluations/`. Current automated checks verify deterministic output, duplicate-behavior sanity, tenant retrieval boundaries, pair comparison persistence, citation validity, insufficient-market-evidence behavior, and professional disclaimers.

No production accuracy claim is made. The synthetic set is too small and unlike real collections. It does not support reported Precision@K, Recall@K, segmentation IoU, valuation MAE, or agent groundedness rates.

Promotion gates for a domain model require:

1. A licensed manifest, hashes, environment capture, seeded split, and expert-authored labels.
2. Retrieval Precision@K/Recall@K and false-positive slices by transformation and medium.
3. Conservation change/segmentation metrics with lighting, camera, viewpoint, and substrate slices.
4. Valuation MAE, median absolute error, interval coverage, time split, and category coverage using licensed transactions.
5. Agent tool success, citation validity, unsupported-claim rate, escalation correctness, injection resistance, latency, and actual provider cost.
6. A recorded human decision to promote a version from development status.

`make performance` reports observed local primitive latency and process memory without extrapolating concurrency. Evaluation results must record failures as well as successes.
