---
wave: 1
depends_on: []
files_modified:
  - neopulse/DoctorDashboard.tsx
  - neopulse/neopulse.html
autonomous: true
---

# Phase 05: Doctor Portal & UI Polish (Plan 01)

## Objective
Build the clinical visualization portal to aggregate vital sign history across multiple patients and synchronize the frontend AR bounding boxes with the SSE backend latency.

## Requirements
- **PORTAL-01**: User can view a dashboard containing multiple patient vital histories.
- **PORTAL-02**: System aggregates vital sign telemetry into time-series graphs for Doctor review.
- **UI-01**: Bounding box overlay synchronizes with SSE stream latency to avoid drift.

## Tasks

### 1. Implement Doctor Portal Dashboard
**Description:** Implement `DoctorDashboard.tsx` as a React-based interface for visualizing historical telemetry data for multiple patients.
<read_first>
- .planning/REQUIREMENTS.md
- neopulse/DoctorDashboard.tsx (if exists)
</read_first>
<action>
Modify `neopulse/DoctorDashboard.tsx`:
- Import React and charting libraries (like Recharts if applicable, or generic canvas rendering).
- Create a `DoctorDashboard` component that manages a `patients` array state.
- Render a list of patients.
- When a patient is selected, render a time-series graph mapping historical HR and RR values over time.
</action>
<acceptance_criteria>
- `neopulse/DoctorDashboard.tsx` contains `const DoctorDashboard` or `function DoctorDashboard`
- `neopulse/DoctorDashboard.tsx` contains state for `patients`
- `neopulse/DoctorDashboard.tsx` maps over telemetry arrays to render graphs or visual lists
</acceptance_criteria>

### 2. Synchronize AR Overlay with SSE Latency
**Description:** Address the technical debt from v1.0 by ensuring the computer vision bounding box in `neopulse.html` does not drift from the video feed when SSE chunks lag.
<read_first>
- neopulse/neopulse.html
</read_first>
<action>
Modify `neopulse/neopulse.html`:
- Inside `processFrame()`, add a smoothing interpolation factor for the `x, y, w, h` coordinates of the face and chest ROI boxes.
- Introduce a queue mechanism `const boxQueue = []` that pushes backend bounding box coordinates upon SSE tick, and interpolates between them frame-by-frame instead of instantly snapping.
</action>
<acceptance_criteria>
- `neopulse/neopulse.html` contains `boxQueue` or similar interpolation logic
- `neopulse/neopulse.html` smoothly draws the ROI rectangle in `processFrame`
</acceptance_criteria>

## Verification
- Verify the React dashboard is structurally sound.
- Verify `neopulse.html` has logic for smoothing/queueing the bounding box AR tracking.
