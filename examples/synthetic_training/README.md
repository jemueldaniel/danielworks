# Synthetic training and honest held-out evaluation

A **real, small CPU optimizer**, independently authored as a public example with Python's standard library. No connection, account, API, external dataset, downloaded model, GPU or proprietary source is required. It does **not** demonstrate training an LLM, distributed/federated learning, model serving, or production-grade MLOps.

The default demonstration creates a deterministic, balanced, labelled **synthetic** binary-classification dataset with three numeric features. A stratified 60/20/20 train/validation/test partition uses non-overlapping row identities. Feature means and standard deviations are fit using only the **training** partition. A bounded minibatch gradient-descent optimizer fits binary logistic regression with L2 regularization and gradient clipping. The validation split selects the best checkpoint; the test split is evaluated **only after training completes**. Accuracy is compared with the fixed majority-class baseline from training labels.

`train()` accepts a validated tuple of rows; the provided CLI and tests generate their own toy data. Inputs are not read from any external file or service, and no results are sent anywhere.

## Run

```sh
python -B examples/synthetic_training/demo.py
python -B -m unittest discover -s examples/synthetic_training -v
```

`demo.py` explicitly stops after eight epochs, JSON-round-trips the in-memory checkpoint, then resumes without repeating epochs. The uninterrupted/continued equivalence and deterministic seed behavior are checked in the 17 tests. The checkpoint SHA-256 detects accidental changes only: it is **not an authenticated signature, encrypted model, durable transaction log, or secure serialization boundary**. Any future durable storage or multi-worker design must add trusted persistence, identity and concurrency controls.

### Observed on Python 3.13.5 (Linux, 11 October 2026)

| Metric | Locally observed value |
|---|---:|
| Generated samples (train / validation / test) | 240 / 80 / 80 |
| Training epochs completed | 70 |
| Validation accuracy | 0.925 |
| Held-out synthetic test accuracy | 0.9875 |
| Majority-class baseline test accuracy | 0.5000 |
| Regression tests | 17 passed, no failures |

These are **toy-data results, not real-world generalization benchmarks**; another dataset or operating environment can behave differently. The raw selected model/metrics remain inspectable in [`training.py`](training.py) and [`demo.py`](demo.py). The source itself contains no private dataset or business feature.

## What the tests refuse

Out-of-budget epochs/batches, nonfinite parameters, malformed rows, inconsistent checkpoints, changed input identities or training configuration, stale/forged progress, premature completion, unknown checkpoint fields, altered hashes, overlapping splits, and accidental preprocessing leakage from the test partition. Failing these cases is intentional. No external effects or production guarantees are claimed.
