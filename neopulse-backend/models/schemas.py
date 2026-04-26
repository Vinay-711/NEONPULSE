from pydantic import BaseModel
from typing import Optional

class VitalSigns(BaseModel):
    hr_bpm: float
    rr_bpm: float
    confidence: float
    timestamp: float
    alert_state: str

class AlertEvent(BaseModel):
    state: str
    title: str
    message: str
    timestamp: float

class AnalysisResult(BaseModel):
    vitals: VitalSigns
    alert: Optional[AlertEvent]
    frame_number: int
