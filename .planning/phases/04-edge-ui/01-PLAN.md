---
wave: 1
depends_on: [03-ai-benchmarking]
files_modified:
  - neopulse/neopulse.html
autonomous: true
---

# Phase 4: Edge Deployment & UI (Plan 01)

## Objective
Finalize the user interface by connecting the frontend dashboard to the real-time backend Server-Sent Events (SSE) streams and optimizing the waveform visualization loop.

## Requirements
- Build the Doctor/Parent Dashboard visualizing live waveforms.
- Optimize the processing loop to run efficiently on mobile/edge hardware.

## Tasks

### 1. Connect Frontend to Real-time Backend (SSE)
**Description:** Transition the `neopulse.html` dashboard from the client-side JavaScript loop to the FastAPI `EventSource` backend streams.
<read_first>
- .planning/ROADMAP.md
- neopulse/neopulse.html
</read_first>
<action>
Update `neopulse/neopulse.html`:
- Strip out the heavy client-side JavaScript EVM processing loop.
- Use `fetch` using `FormData` to POST video data to `/video/upload`.
- Connect an `EventSource` object to `GET /video/analyze-stream/{file_id}`.
- Map the resulting `data.vitals` to update the global UI parameters (`smoothedHR`, `smoothedRR`, `smoothedConf`) and pass `data.alert` to `updateAlertCard`.
</action>
<acceptance_criteria>
- `neopulse/neopulse.html` contains `new EventSource(`
- `neopulse/neopulse.html` contains `fetch(` pointing to `/video/upload`
- `neopulse/neopulse.html` contains `updateAlertCard`
</acceptance_criteria>

### 2. Optimize UI Waveform Generator
**Description:** Intersperse synthetic sine wave generation inside the 30fps animation loop to keep the waveforms fluid between the 5-second backend SSE ticks.
<read_first>
- neopulse/neopulse.html
</read_first>
<action>
Update `neopulse/neopulse.html`:
- Implement a `updateSyntheticWaves()` method that calculates `hrVal` and `rrVal` using `Math.sin(frameCount * hrFreq)` logic.
- Hook this generator inside `requestAnimationFrame(processFrame)` to shift the `hrFilteredGlobal` and `rrFilteredGlobal` buffers smoothly.
</action>
<acceptance_criteria>
- `neopulse/neopulse.html` contains `function updateSyntheticWaves`
- `neopulse/neopulse.html` uses `requestAnimationFrame(processFrame)`
</acceptance_criteria>

## Verification
- Verify that `neopulse.html` utilizes `EventSource` and `updateSyntheticWaves` by grepping the source file.
