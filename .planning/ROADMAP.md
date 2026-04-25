# Project Roadmap

## Phase 1: Core Signal Pipeline
**Goal:** Establish the foundational Eulerian Video Magnification (EVM) pipeline for extracting physiological signals.
- Set up real-time video capture framework.
- Implement spatial decomposition and temporal bandpass filtering (0.1-0.8Hz for RR, 0.8-3.0Hz for HR).
- Extract raw 1D signal arrays from video frames.

## Phase 2: Rate Estimation & Heuristics
**Goal:** Convert raw signals into actionable BPM and breathing rates with clinical thresholds.
- Implement peak detection algorithms over the filtered signals.
- Calculate signal confidence scores based on interval standard deviations.
- Build the deterministic rule-based alert engine (Normal, Caution, Emergency).

## Phase 3: AI Integration & Benchmarking
**Goal:** Train and integrate the machine learning classifier using PhysioNet datasets.
- Extract features (mean HR, std HR, RR interval) from Apnea-ECG/NInFEA datasets.
- Train and deploy the Random Forest classifier.
- Validate system accuracy (MAE, RMSE, Pearson R) against ground truth ECG.

## Phase 4: Edge Deployment & UI
**Goal:** Finalize the user interface and ensure offline capability.
- Build the Doctor/Parent Dashboard visualizing live waveforms.
- Optimize the processing loop to run efficiently on mobile/edge hardware.
