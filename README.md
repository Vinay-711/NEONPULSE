# NeoPulse Diagnostic Platform

A real-time, clinical-grade neonatal vitals monitoring system using camera-based rPPG (EVM) and machine-learning-driven apnea detection.

## Quick Start

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Start the Backend
Open a terminal, navigate to the project root, and execute the backend startup script. This will automatically install dependencies, download the PhysioNet clinical datasets (Apnea-ECG & NInFEA), and start the FastAPI server.
```bash
bash start.sh
```
*Wait for the message: `Application startup complete`.*

### 3. Start the Frontend
Open a second terminal, navigate to the project root, and run:
```bash
bash start_frontend.sh
```

### 4. Open the Application
Launch Google Chrome and navigate to:
[http://localhost:5500/neopulse.html](http://localhost:5500/neopulse.html)

### 5. Verify Backend Connection
Click the **"Load dataset sample"** button in the UI. Select a record from the dropdown. This confirms the backend dataset router is actively communicating with the PhysioNet integration.

### 6. Run Video Analysis
Drag and drop any MP4/MOV/WebM video into the upload zone and click **Start Analysis** to stream real-time EVM data from the backend.

---

## Troubleshooting

### CORS Errors in Browser Console
If you see a CORS error when attempting to upload a video or fetch datasets:
- Ensure the backend is actively running on port `8000`.
- Verify you are accessing the frontend via `localhost:5500` (not `127.0.0.1` or directly via `file://`), as the backend strictly whitelists origins.

### Port Already In Use
If either script fails due to an occupied port (e.g. `[Errno 48] Address already in use`):
- Run `lsof -i :8000` (for backend) or `lsof -i :5500` (for frontend) to find the PID.
- Run `kill -9 <PID>` to free up the port, then try the script again.

### WFDB Dataset Download Timeout
The PhysioNet databases (`apnea-ecg`, `ninfea`) are quite large.
- If the `start.sh` script hangs or throws a timeout during the Python script phase, abort using `Ctrl+C`.
- Try running the script again. The `wfdb` library automatically detects partially downloaded files and will resume from where it failed.
