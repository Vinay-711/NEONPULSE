# Requirements: v1.1 Security & Portal

## 1. Doctor Portal
- [ ] **PORTAL-01**: User can view a dashboard containing multiple patient vital histories.
- [ ] **PORTAL-02**: System aggregates vital sign telemetry into time-series graphs for Doctor review.

## 2. Authentication
- [ ] **AUTH-01**: User must authenticate via Firebase before accessing the telemetry stream.
- [ ] **AUTH-02**: Backend rejects any video upload or SSE connection without a valid Firebase Bearer token.

## 3. UI Optimization
- [ ] **UI-01**: Bounding box overlay synchronizes with SSE stream latency to avoid drift.

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| PORTAL-01 | 05 | Pending |
| PORTAL-02 | 05 | Pending |
| AUTH-01   | 06 | Pending |
| AUTH-02   | 06 | Pending |
| UI-01     | 05 | Pending |
