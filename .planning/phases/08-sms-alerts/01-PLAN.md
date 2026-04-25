---
wave: 1
depends_on: [07-cloud-sync]
files_modified:
  - neopulse-backend/services/alerts.py
  - neopulse-backend/routers/video.py
autonomous: true
---

# Phase 08: SMS/Email Alerting (Plan 01)

## Objective
Wire the alert pipeline to a third-party SMS dispatch service to ensure emergency contacts are immediately notified upon detecting critical vital thresholds.

## Requirements
- **ALERT-01**: System dispatches SMS/Email to emergency contacts when EMERGENCY state is triggered.

## Tasks

### 1. Create Alert Dispatcher Service
**Description:** Build the `services/alerts.py` module to handle third-party Twilio/SendGrid integration logic.
<read_first>
- .planning/REQUIREMENTS.md
</read_first>
<action>
Create `neopulse-backend/services/alerts.py`:
- Implement a `dispatch_emergency_alert(file_id, hr_bpm, rr_bpm)` function.
- Include logic to send an SMS/Email (can use `print()` mocks or actual `requests` calls to Twilio).
- Ensure the payload clearly states the file/patient ID and the failing vitals.
</action>
<acceptance_criteria>
- `neopulse-backend/services/alerts.py` contains `def dispatch_emergency_alert`
</acceptance_criteria>

### 2. Wire Alerts into Video Telemetry Router
**Description:** Connect the alerting service to the SSE pipeline and add a debouncing mechanism to prevent spam.
<read_first>
- neopulse-backend/routers/video.py
</read_first>
<action>
Modify `neopulse-backend/routers/video.py`:
- Import `dispatch_emergency_alert`.
- In `analyze_stream`, define a `last_alert_time` dictionary or variable.
- When `state == "EMERGENCY"`, check if `time.time() - last_alert_time > 60` (debounce 1 minute).
- If true, call `dispatch_emergency_alert(file_id, hr_bpm, rr_bpm)` asynchronously or in a thread to prevent blocking the video frame processing loop.
</action>
<acceptance_criteria>
- `neopulse-backend/routers/video.py` imports `dispatch_emergency_alert`
- `neopulse-backend/routers/video.py` contains debounce logic tracking `time.time()`
</acceptance_criteria>

## Verification
- Verify the `dispatch_emergency_alert` function exists.
- Verify the router implements the 60-second debounce mechanism around the alert dispatch.
