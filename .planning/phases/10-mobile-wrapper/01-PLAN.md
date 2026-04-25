---
wave: 1
depends_on: [09-edge-ai]
files_modified:
  - neopulse/capacitor.config.json
  - neopulse/package.json
autonomous: true
---

# Phase 10: Native Mobile Wrapper (Plan 01)

## Objective
Bundle the frontend application using Capacitor to allow native deployment of NeoPulse to iOS and Android devices.

## Requirements
- **MOBILE-01**: The web dashboard is bundled into a native mobile shell (e.g., Capacitor or React Native Webview) for iOS and Android deployment.

## Tasks

### 1. Initialize Capacitor
**Description:** Add Capacitor configuration to the frontend directory to enable the mobile bridging layer.
<read_first>
- .planning/REQUIREMENTS.md
</read_first>
<action>
Modify the project to add `neopulse/capacitor.config.json` and a generic `package.json` with Capacitor dependencies if it doesn't already exist.
- `appId`: `com.neopulse.health`
- `appName`: `NeoPulse`
- `webDir`: `.` (or the specific dist folder if one is used).
</action>
<acceptance_criteria>
- `neopulse/capacitor.config.json` exists
- `appId` is configured as `com.neopulse.health`
</acceptance_criteria>

### 2. Configure Android/iOS Build Stubs
**Description:** Prepare the frontend for `npx cap add android` by defining the core capacitor dependencies in `package.json`.
<read_first>
- neopulse/package.json
</read_first>
<action>
Modify `neopulse/package.json`:
- Ensure `@capacitor/core` and `@capacitor/cli` are listed in the dependencies or devDependencies.
- Add an `android` and `ios` devDependency (e.g. `@capacitor/android`).
</action>
<acceptance_criteria>
- `neopulse/package.json` contains `@capacitor/core`
</acceptance_criteria>

## Verification
- Verify the existence and correctness of `capacitor.config.json`.
- Verify `package.json` contains the required Capacitor packages.
