# NeoPulse AI

## Overview
NeoPulse AI is a non-contact neonatal monitoring system that uses a smartphone camera and AI to detect early signs of abnormal breathing and heart rate in newborns.

## Core Value
Provides affordable, hardware-free monitoring to enable early detection of neonatal risks at home, particularly for underserved rural populations.

## Current State (v2.0 Production & Mobile)
Evolved NeoPulse into a production-ready edge platform. Telemetry runs natively on mobile devices via Capacitor wrapping the web dashboard. Inference is slashed via `onnxruntime`, Cloud Firestore backs up historical sessions, and an emergency pipeline automatically dispatches 60-second debounced Twilio SMS warnings.



## Target Audience
- New parents (especially rural/underserved)
- Healthcare workers (ASHA, nurses)
- Pediatricians (for remote monitoring)

## Key Constraints & Boundaries
- Must work in low connectivity (offline support/edge AI).
- Must operate effectively despite lighting variability and baby movement noise.
- Needs high sensitivity detection with minimal false negative rate.
- Must ensure strict access control via Authorization layers.

## Requirements

### Validated
- ✓ Capture real-time video input via smartphone camera (v1.0)
- ✓ Extract breathing signal using computer vision (EVM) (v1.0)
- ✓ Estimate heart rate (experimental) (v1.0)
- ✓ AI-based anomaly detection for risk alerts (v1.0)
- ✓ Provide simple dashboard for caregivers/doctors (v1.0)
- ✓ Doctor Portal Dashboard for historical multi-patient visualization (v1.1)
- ✓ Firebase Auth for clinical data protection (v1.1)
- ✓ Synchronize UI AR overlay with backend latency for perfectly smooth bounding box tracking (v1.1)
- ✓ Cloud Database Sync (v2.0)
- ✓ SMS/Email Emergency Alerts (v2.0)
- ✓ Edge AI Optimization (ONNX) (v2.0)
- ✓ Native Mobile App Wrapper (v2.0)

### Active
(None yet — planning next milestone)

### Out of Scope
- Direct medical diagnosis (it is strictly an assistive tool for risk detection)
- Proprietary hardware sensors (must rely entirely on smartphone cameras)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Smartphone-only | Accessibility for rural populations | ✓ Good |
| Eulerian Video Magnification | Industry standard for non-contact micro-motion | ✓ Good |
| Server-Sent Events | Unidirectional telemetry is lightweight | ✓ Good |
| Query Parameter Auth | EventSource doesn't support headers | ✓ Good |
| ONNX Runtime | Slashes Scikit-Learn memory overhead | ✓ Good |
| Capacitor Mobile Shell | Wraps existing DOM APIs seamlessly | ✓ Good |

---
*Last updated: 2026-04-26 after v1.1 milestone*
