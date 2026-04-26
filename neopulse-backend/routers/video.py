from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import os
import cv2
import base64
import json
import time
import asyncio
from config import DATA_DIR, HR_NORMAL, RR_NORMAL
from services.evm import (
    extract_rppg_signal, 
    extract_motion_signal, 
    bandpass_filter, 
    estimate_heart_rate, 
    estimate_breathing_rate
)
from services.alerts import dispatch_emergency_alert

router = APIRouter(prefix="/video", tags=["Video"])

def verify_token(authorization: str = Header(None), token: str = None):
    # Accept token either from Bearer header or query parameter (for EventSource)
    token_str = token
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ")[1]
        
    if not token_str or token_str != "MOCK_FIREBASE_TOKEN":
        raise HTTPException(status_code=401, detail="Invalid or missing Firebase Auth token")
    return token_str

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    uploads_dir = os.path.join(DATA_DIR, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(uploads_dir, f"{file_id}.mp4")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Invalid video file")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    duration_sec = total_frames / fps if fps > 0 else 0
    
    return {
        "file_id": file_id,
        "duration_sec": duration_sec,
        "fps": fps,
        "resolution": f"{width}x{height}",
        "total_frames": total_frames
    }

class ExtractRequest(BaseModel):
    file_id: str
    start_sec: float
    end_sec: float
    max_frames: int = 300

@router.post("/extract-frames")
def extract_frames(req: ExtractRequest):
    file_path = os.path.join(DATA_DIR, 'uploads', f"{req.file_id}.mp4")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
        
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    start_frame = int(req.start_sec * fps)
    end_frame = int(req.end_sec * fps)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    frames_b64 = []
    frame_count = 0
    
    while cap.isOpened() and frame_count < req.max_frames:
        curr_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if curr_frame >= end_frame:
            break
            
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_resized = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', frame_resized)
        b64 = base64.b64encode(buffer).decode('utf-8')
        frames_b64.append(b64)
        
        frame_count += 1
        
    cap.release()
    
    return {
        "frames": frames_b64,
        "fps": fps,
        "frame_count": frame_count
    }

@router.get("/analyze-stream/{file_id}")
async def analyze_stream(
    file_id: str,
    token: str = Depends(verify_token)
):
    file_path = os.path.join(DATA_DIR, 'uploads', f"{file_id}.mp4")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
        
    async def event_generator():
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if fps <= 0:
            fps = 30.0
            
        chunk_sec = 5.0
        chunk_frames = int(chunk_sec * fps)
        
        frames = []
        processed_frames = 0
        last_alert_time = 0  # Initialize debounce tracker
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
            processed_frames += 1
            
            if len(frames) >= chunk_frames:
                # Process EVM for this chunk
                raw_rppg = extract_rppg_signal(frames)
                raw_motion = extract_motion_signal(frames)
                
                filtered_hr = bandpass_filter(raw_rppg, fps, 0.8, 3.0)
                filtered_rr = bandpass_filter(raw_motion, fps, 0.1, 0.8)
                
                hr_bpm, hr_conf = estimate_heart_rate(filtered_hr, fps)
                rr_bpm, rr_conf = estimate_breathing_rate(filtered_rr, fps)
                
                overall_confidence = (hr_conf + rr_conf) / 2.0 * 100.0
                
                state = "NORMAL"
                title = "ALL NORMAL"
                msg = "Vitals are within expected ranges"
                
                if hr_bpm < 80 or hr_bpm > 180 or rr_bpm < 20 or rr_bpm > 70:
                    state = "EMERGENCY"
                    title = "EMERGENCY"
                    msg = "Critical vitals detected. Go to hospital now."
                    
                    # Fire debounced alert dispatch
                    current_time = time.time()
                    if current_time - last_alert_time > 60:
                        asyncio.create_task(
                            asyncio.to_thread(dispatch_emergency_alert, file_id, hr_bpm, rr_bpm)
                        )
                        last_alert_time = current_time

                elif (hr_bpm >= 80 and hr_bpm < HR_NORMAL[0]) or (hr_bpm > HR_NORMAL[1] and hr_bpm <= 180) or \
                     (rr_bpm >= 20 and rr_bpm < RR_NORMAL[0]) or (rr_bpm > RR_NORMAL[1] and rr_bpm <= 70):
                    state = "CAUTION"
                    title = "CAUTION"
                    msg = "Vitals borderline — watch closely"
                    
                alert_dict = {
                    "state": state,
                    "title": title,
                    "message": msg,
                    "timestamp": time.time()
                } if state != "NORMAL" else None
                
                vitals_dict = {
                    "hr_bpm": float(hr_bpm),
                    "rr_bpm": float(rr_bpm),
                    "confidence": float(overall_confidence),
                    "timestamp": time.time(),
                    "alert_state": state
                }
                
                progress_pct = min(100.0, (processed_frames / total_frames) * 100.0) if total_frames > 0 else 100.0
                
                data = {
                    "vitals": vitals_dict,
                    "alert": alert_dict,
                    "progress_pct": progress_pct
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                frames = [] # clear chunk
                
                # Prevent blocking the event loop entirely
                await asyncio.sleep(0.01) 
                
        cap.release()
        
        # End stream
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
