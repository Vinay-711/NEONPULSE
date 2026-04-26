from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import numpy as np
import cv2
import time
from services.evm import (
    extract_rppg_signal, 
    extract_motion_signal, 
    bandpass_filter, 
    estimate_heart_rate, 
    estimate_breathing_rate
)
from models.schemas import AnalysisResult, VitalSigns, AlertEvent
from config import HR_NORMAL, RR_NORMAL

router = APIRouter(prefix="/signals", tags=["Signals"])

class AnalysisRequest(BaseModel):
    frames_base64: list[str]
    fps: float

@router.post("/analyze", response_model=AnalysisResult)
def analyze_signals(req: AnalysisRequest):
    if not req.frames_base64:
        raise HTTPException(status_code=400, detail="No frames provided")
        
    fps = req.fps
    if fps <= 0:
        raise HTTPException(status_code=400, detail="Invalid FPS")

    # Decode frames
    frames = []
    for b64 in req.frames_base64:
        try:
            if ',' in b64:
                b64 = b64.split(',', 1)[1]
            img_data = base64.b64decode(b64)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                frames.append(img)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 frame data")
            
    if not frames:
        raise HTTPException(status_code=400, detail="No valid frames decoded")
            
    # Process Signals
    raw_rppg = extract_rppg_signal(frames)
    raw_motion = extract_motion_signal(frames)
    
    # Filter (HR: 48-180 BPM, RR: 6-48 br/min)
    filtered_hr = bandpass_filter(raw_rppg, fps, 0.8, 3.0)
    filtered_rr = bandpass_filter(raw_motion, fps, 0.1, 0.8)
    
    # Estimate Rates
    hr_bpm, hr_conf = estimate_heart_rate(filtered_hr, fps)
    rr_bpm, rr_conf = estimate_breathing_rate(filtered_rr, fps)
    
    # Aggregate Confidence
    overall_confidence = (hr_conf + rr_conf) / 2.0 * 100.0
    
    # State classification
    state = "NORMAL"
    title = "ALL NORMAL"
    msg = "Vitals are within expected ranges"
    
    if hr_bpm < 80 or hr_bpm > 180 or rr_bpm < 20 or rr_bpm > 70:
        state = "EMERGENCY"
        title = "EMERGENCY"
        msg = "Critical vitals detected. Go to hospital now."
    elif (hr_bpm >= 80 and hr_bpm < HR_NORMAL[0]) or (hr_bpm > HR_NORMAL[1] and hr_bpm <= 180) or \
         (rr_bpm >= 20 and rr_bpm < RR_NORMAL[0]) or (rr_bpm > RR_NORMAL[1] and rr_bpm <= 70):
        state = "CAUTION"
        title = "CAUTION"
        msg = "Vitals borderline — watch closely"
        
    alert = AlertEvent(
        state=state,
        title=title,
        message=msg,
        timestamp=time.time()
    ) if state != "NORMAL" else None
    
    return AnalysisResult(
        vitals=VitalSigns(
            hr_bpm=hr_bpm,
            rr_bpm=rr_bpm,
            confidence=overall_confidence,
            timestamp=time.time(),
            alert_state=state
        ),
        alert=alert,
        frame_number=len(frames)
    )
