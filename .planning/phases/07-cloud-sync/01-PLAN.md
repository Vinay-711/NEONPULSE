---
wave: 1
depends_on: []
files_modified:
  - neopulse/neopulse.html
autonomous: true
---

# Phase 07: Cloud Database Sync (Plan 01)

## Objective
Integrate real-time Firestore syncing to backup neonatal telemetry data to the cloud, powering the Doctor Portal.

## Requirements
- **SYNC-01**: System syncs local telemetry state to a remote Firestore database in real-time.

## Tasks

### 1. Initialize Firestore Database Sync
**Description:** Implement Firestore document creation during the SSE tick cycle to push live vitals to the cloud.
<read_first>
- neopulse/neopulse.html
</read_first>
<action>
Modify `neopulse/neopulse.html`:
- Import `getFirestore`, `collection`, and `addDoc` from Firebase SDK (assuming the SDK is already imported via CDN or module in the environment).
- Inside the `eventSource.onmessage` handler, after parsing `data.vitals`, push the telemetry event to the Firestore database at the path `sessions/${activeFileId}/events`.
- Store the payload exactly as the `DoctorDashboard.tsx` expects it (e.g. `hr_bpm`, `rr_bpm`, `timestamp`, `alert_state`).
</action>
<acceptance_criteria>
- `neopulse/neopulse.html` contains `addDoc(collection(`
- `neopulse/neopulse.html` contains `sessions/${activeFileId}/events`
</acceptance_criteria>

## Verification
- Verify that the Firestore `addDoc` command successfully injects telemetry chunks upon the SSE tick cycle.
