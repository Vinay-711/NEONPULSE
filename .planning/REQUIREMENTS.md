# Requirements: v2.0 Production & Mobile

## 1. Cloud Sync
- [ ] **SYNC-01**: System syncs local telemetry state to a remote Firestore database in real-time.

## 2. Alerting
- [ ] **ALERT-01**: System dispatches SMS/Email notifications (e.g. via Twilio/SendGrid) to pre-configured emergency contacts when the EMERGENCY state is triggered.

## 3. Edge AI Optimization
- [ ] **EDGE-01**: The Random Forest Apnea classification model is exported to ONNX or TensorFlow Lite to reduce memory footprint.
- [ ] **EDGE-02**: Fast inference engine replaces Scikit-Learn for prediction on limited hardware.

## 4. Mobile Wrapper
- [ ] **MOBILE-01**: The web dashboard is bundled into a native mobile shell (e.g., Capacitor or React Native Webview) for iOS and Android deployment.

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| SYNC-01  | 07 | Pending |
| ALERT-01 | 08 | Pending |
| EDGE-01  | 09 | Pending |
| EDGE-02  | 09 | Pending |
| MOBILE-01| 10 | Pending |
