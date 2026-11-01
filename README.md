# NeoPulse — Signal-Monitoring Research Prototype

A research demonstration exploring camera-derived signals, rPPG/EVM and experimental apnea classification. It is not a clinically validated neonatal monitor, diagnostic device or emergency alert service.

## Components

| Path | Purpose |
| --- | --- |
| [neopulse-backend](neopulse-backend) | FastAPI signal, video, dataset and alert routes |
| [neopulse/neopulse.html](neopulse/neopulse.html) | Browser demonstration |
| [neopulse/evaluation_harness.py](neopulse/evaluation_harness.py) | Experimental evaluation entry point |
| [neopulse](neopulse) | Signal processing and model experiments |

## Local setup

Use a Python environment compatible with the dependencies in [neopulse-backend/requirements.txt](neopulse-backend/requirements.txt). From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r neopulse-backend/requirements.txt
cd neopulse-backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```sh
python3 -m http.server 8080 --directory neopulse
```

Open http://localhost:8080/neopulse.html. The API is a separate process on port 8000. The root `start.sh` only starts Uvicorn; it does not install dependencies or prove dataset availability. `start_frontend.sh` serves the browser page on port 8080.

## Evaluation and data boundaries

Record dataset version, train/test separation, signal quality, device conditions and uncertainty when reporting results. Inspect dataset-loader behavior and applicable dataset access/use conditions before retrieving or redistributing data. A dataset-router response or a generated signal is not clinical accuracy evidence.

Use de-identified or synthetic examples. Do not commit infant videos or patient records. No fresh build, evaluation run, clinical sensitivity/specificity result or alert-delivery guarantee is asserted by this documentation update.

## Review checklist

Check API-offline behavior, invalid video uploads, empty/noisy signals, permissions, and clear distinction between demonstrations and measured signals. Any prospective clinical application needs separate validation, qualified review and an appropriate deployment process.

### Motion extraction regression checks

Install `requirements-signal-test.txt`, then run
`python -m pytest tests/test_motion_signal.py -q` with Python 3.14.
The lightweight suite checks frame-to-sample alignment, empty regions, resolution
changes, and ordinary motion differences without models or patient data. Missing
regions and changed ROI shapes start a new baseline with a zero sample; this preserves
timing but is not a clinical confidence or validity guarantee. GitHub Actions runs
the same checks on pull requests and pushes to `master`.
