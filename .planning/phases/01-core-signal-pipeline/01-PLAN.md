---
wave: 1
depends_on: []
files_modified:
  - neopulse-backend/services/evm.py
  - neopulse-backend/routers/signals.py
autonomous: true
---

# Phase 1: Core Signal Pipeline (Plan 01)

## Objective
Establish the foundational Eulerian Video Magnification (EVM) pipeline for extracting physiological signals from raw video frames.

## Requirements
- Set up real-time video capture framework.
- Implement spatial decomposition and temporal bandpass filtering (0.1-0.8Hz for RR, 0.8-3.0Hz for HR).
- Extract raw 1D signal arrays from video frames.

## Tasks

### 1. Implement Core EVM Engine
**Description:** Implement the mathematical pipeline for rPPG (Face ROI) and Motion (Chest ROI) extraction using NumPy and SciPy.
<read_first>
- .planning/PROJECT.md
- neopulse-backend/services/evm.py (if exists)
</read_first>
<action>
Create `neopulse-backend/services/evm.py` with:
- `extract_rppg_signal` function (Green - 0.5*Red - 0.5*Blue)
- `extract_motion_signal` function (mean absolute pixel diff)
- `bandpass_filter` using scipy.signal.butter (4th order)
- Return 1D numpy arrays for the signals.
</action>
<acceptance_criteria>
- `neopulse-backend/services/evm.py` contains `def extract_rppg_signal`
- `neopulse-backend/services/evm.py` contains `def extract_motion_signal`
- `neopulse-backend/services/evm.py` contains `def bandpass_filter`
</acceptance_criteria>

### 2. Implement Video Router
**Description:** Build the FastAPI router for processing video streams and extracting frames for the EVM pipeline.
<read_first>
- .planning/PROJECT.md
- neopulse-backend/routers/signals.py (if exists)
</read_first>
<action>
Create `neopulse-backend/routers/signals.py` exposing FastAPI endpoints that decode base64 frames using OpenCV and trigger the EVM processing pipeline.
</action>
<acceptance_criteria>
- `neopulse-backend/routers/signals.py` contains an APIRouter
- `neopulse-backend/routers/signals.py` contains at least one POST endpoint for signal processing
</acceptance_criteria>

## Verification
- Run `pytest` or verify that the `evm.py` module can be imported without syntax errors.
- Ensure all acceptance criteria are met via grep.
