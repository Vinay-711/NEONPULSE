# NeoPulse AI

## Overview
NeoPulse AI is a non-contact neonatal monitoring system that uses a smartphone camera and AI to detect early signs of abnormal breathing and heart rate in newborns.

## Core Value
Provides affordable, hardware-free monitoring to enable early detection of neonatal risks at home, particularly for underserved rural populations.

## Current State (v1.0 MVP)
Shipped the core foundation of NeoPulse. Transitioned the initial frontend prototype to a robust Python-based backend that handles Server-Sent Events, runs the EVM pipeline with SciPy, and utilizes a Scikit-Learn Random Forest model for Apnea detection.

## Target Audience
- New parents (especially rural/underserved)
- Healthcare workers (ASHA, nurses)
- Pediatricians (for remote monitoring)

## Key Constraints & Boundaries
- Must work in low connectivity (offline support/edge AI).
- Must operate effectively despite lighting variability and baby movement noise.
- Needs high sensitivity detection with minimal false negative rate.

## Requirements

### Validated
- ✓ Capture real-time video input via smartphone camera (v1.0)
- ✓ Extract breathing signal using computer vision (EVM) (v1.0)
- ✓ Estimate heart rate (experimental) (v1.0)
- ✓ AI-based anomaly detection for risk alerts (v1.0)
- ✓ Provide simple dashboard for caregivers/doctors (v1.0)

### Active
- [ ] Implement Doctor Portal Dashboard for historical multi-patient visualization.
- [ ] Add Firebase Auth for clinical data protection.
- [ ] Synchronize UI AR overlay with backend latency for perfectly smooth bounding box tracking.

### Out of Scope
- Direct medical diagnosis (it is strictly an assistive tool for risk detection)
- Proprietary hardware sensors (must rely entirely on smartphone cameras)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Smartphone-only | Accessibility for rural populations | ✓ Good |
| Eulerian Video Magnification | Industry standard for non-contact micro-motion | ✓ Good |
| Server-Sent Events | Unidirectional telemetry is lightweight | ✓ Good |

---
*Last updated: 2026-04-26 after v1.0 MVP milestone*
