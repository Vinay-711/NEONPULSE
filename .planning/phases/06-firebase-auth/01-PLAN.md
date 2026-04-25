---
wave: 1
depends_on: [05-doctor-portal]
files_modified:
  - neopulse-backend/routers/video.py
  - neopulse/neopulse.html
autonomous: true
---

# Phase 06: Firebase Auth Middleware (Plan 01)

## Objective
Secure the clinical data pipeline by requiring Firebase Authentication for all telemetry access and video uploads.

## Requirements
- **AUTH-01**: User must authenticate via Firebase before accessing the telemetry stream.
- **AUTH-02**: Backend rejects any video upload or SSE connection without a valid Firebase Bearer token.

## Tasks

### 1. Implement FastAPI Auth Middleware
**Description:** Implement token validation in the backend routers.
<read_first>
- .planning/REQUIREMENTS.md
- neopulse-backend/routers/video.py
</read_first>
<action>
Modify `neopulse-backend/routers/video.py`:
- Add a dummy or real Firebase JWT verification dependency (e.g., `def verify_token(authorization: str = Header(None))`).
- If `authorization` header is missing or invalid, raise an `HTTPException(status_code=401)`.
- Inject `Depends(verify_token)` into the `POST /video/upload` and `GET /video/analyze-stream/{file_id}` endpoints.
</action>
<acceptance_criteria>
- `neopulse-backend/routers/video.py` contains `def verify_token`
- `neopulse-backend/routers/video.py` contains `status_code=401`
- `neopulse-backend/routers/video.py` uses `Depends(verify_token)` in endpoint signatures
</acceptance_criteria>

### 2. Update Frontend Firebase Headers
**Description:** Modify the frontend dashboard to append the authorization header to network requests.
<read_first>
- neopulse/neopulse.html
</read_first>
<action>
Modify `neopulse/neopulse.html`:
- Assume Firebase SDK is initialized globally and a token is retrieved (mock or real).
- Add `Authorization: "Bearer MOCK_FIREBASE_TOKEN"` to the `fetch` options in the `POST /video/upload` method.
- Pass the token as a URL query parameter `?token=MOCK_FIREBASE_TOKEN` for the `EventSource` connection to `/video/analyze-stream/{file_id}` (since standard `EventSource` does not support custom headers).
</action>
<acceptance_criteria>
- `neopulse/neopulse.html` contains `Authorization: "Bearer`
- `neopulse/neopulse.html` contains `?token=` in the `EventSource` URL
</acceptance_criteria>

## Verification
- Verify the token extraction dependency is present in the FastAPI router.
- Verify the frontend explicitly passes the Authorization credential.
