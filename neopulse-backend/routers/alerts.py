from fastapi import APIRouter
from models.schemas import VitalSigns, AlertEvent
from services.classifier import classify_vitals
import time

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/classify", response_model=AlertEvent)
def classify_alert(vitals: VitalSigns):
    # Approximation of HR standard deviation based on confidence
    hr_std_approx = 5.0 * (1.0 - (vitals.confidence / 100.0))
    
    result = classify_vitals(
        hr_bpm=vitals.hr_bpm, 
        rr_bpm=vitals.rr_bpm, 
        hr_std=hr_std_approx, 
        confidence=vitals.confidence
    )
    
    state = result["state"]
    method = result["method"]
    conf = result["confidence"]
    
    if state == "EMERGENCY":
        title = "EMERGENCY"
        msg = f"Critical vitals detected. Go to hospital now. (Source: {method}, Conf: {conf:.1f}%)"
    elif state == "CAUTION":
        title = "CAUTION"
        msg = f"Vitals borderline — watch closely. (Source: {method}, Conf: {conf:.1f}%)"
    else:
        title = "ALL NORMAL"
        msg = f"Vitals are within expected ranges. (Source: {method}, Conf: {conf:.1f}%)"
        
    return AlertEvent(
        state=state,
        title=title,
        message=msg,
        timestamp=time.time()
    )
