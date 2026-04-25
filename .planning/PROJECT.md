# NeoPulse AI

## Overview
NeoPulse AI is a non-contact neonatal monitoring system that uses a smartphone camera and AI to detect early signs of abnormal breathing and heart rate in newborns.

## Core Value
Provides affordable, hardware-free monitoring to enable early detection of neonatal risks at home, particularly for underserved rural populations.

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
(None yet — ship to validate)

### Active
- [ ] Capture real-time video input via smartphone camera
- [ ] Extract breathing signal using computer vision (EVM)
- [ ] Estimate heart rate (experimental)
- [ ] AI-based anomaly detection for risk alerts
- [ ] Provide simple dashboard for caregivers/doctors
- [ ] Offline operation using TensorFlow Lite (Edge AI)

### Out of Scope
- Direct medical diagnosis (it is strictly an assistive tool for risk detection)
- Proprietary hardware sensors (must rely entirely on smartphone cameras)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Smartphone-only | Accessibility for rural populations | — Pending |
| Eulerian Video Magnification | Industry standard for non-contact micro-motion | — Pending |

---
*Last updated: 2026-04-26 after initialization*
