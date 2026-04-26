"""
NeoPulse AI — Fusion Engine
=============================
Combines the frequency-domain Welch PSD vital estimates (Phase 1)
with the CNN classifier output (Phase 2) into a single, more robust
VitalReading using a confidence-weighted fusion strategy.

Why fusion?
-----------
  • PSD (Welch):  good at precise bpm values, poor on transient events
  • CNN:          good at pattern recognition, outputs a class not a bpm
  • Together:     CNN flags the anomaly; PSD provides the numeric value;
                  confidence scores arbitrate when they disagree

Fusion rules
------------
  1. If CNN confidence >= 0.75 AND status != Normal → use CNN status
  2. If PSD confidence >= 0.60 → trust PSD vital values (bpm numbers)
  3. If neither is confident (early buffer, motion artifacts) → status = "Calibrating"
  4. Final alert list merges both sources, deduplicating by message content
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Optional

from neopulse.core.vitals import VitalReading, classify_vitals


CNN_CONFIDENCE_THRESHOLD = 0.72
PSD_CONFIDENCE_THRESHOLD = 0.50
CALIBRATING_LABEL = "Calibrating"


@dataclass
class FusedReading:
    """Extended VitalReading with fusion metadata."""
    heart_rate:        float
    respiration_rate:  float
    skin_tone_index:   float
    confidence:        float
    alerts:            list[str] = field(default_factory=list)
    status:            str = "Normal"
    # Fusion metadata
    cnn_label:         Optional[str] = None
    cnn_confidence:    float = 0.0
    psd_confidence:    float = 0.0
    source:            str = "psd"   # "psd" | "cnn" | "fused" | "calibrating"

    def to_vital_reading(self) -> VitalReading:
        return VitalReading(
            heart_rate=self.heart_rate,
            respiration_rate=self.respiration_rate,
            skin_tone_index=self.skin_tone_index,
            confidence=self.confidence,
            alerts=self.alerts,
            status=self.status,
        )


class FusionEngine:
    """
    Merge PSD-based VitalReading with CNN classifier output.

    Usage
    -----
    engine = FusionEngine()
    fused  = engine.fuse(psd_reading, cnn_label, cnn_confidence, cnn_probs)
    """

    CNN_TO_STATUS = {
        "Normal":       "Normal",
        "Tachycardia":  "Watch",
        "Bradycardia":  "Critical",
        "Tachypnea":    "Watch",
    }

    def fuse(
        self,
        psd_reading: VitalReading,
        cnn_label: Optional[str],
        cnn_confidence: float,
        cnn_probs: Optional[np.ndarray] = None,
    ) -> FusedReading:
        """
        Produce a FusedReading from PSD and CNN outputs.
        Either source may be None / zero-confidence (early pipeline start).
        """

        psd_conf = psd_reading.confidence
        cnn_conf = cnn_confidence if cnn_label else 0.0
        cnn_status = self.CNN_TO_STATUS.get(cnn_label or "", "Normal")

        # ── Calibrating: neither source is ready ──
        if psd_conf < PSD_CONFIDENCE_THRESHOLD and cnn_conf < CNN_CONFIDENCE_THRESHOLD:
            return FusedReading(
                heart_rate=psd_reading.heart_rate,
                respiration_rate=psd_reading.respiration_rate,
                skin_tone_index=psd_reading.skin_tone_index,
                confidence=max(psd_conf, cnn_conf),
                status=CALIBRATING_LABEL,
                alerts=["Building signal — keep camera steady"],
                cnn_label=cnn_label,
                cnn_confidence=cnn_conf,
                psd_confidence=psd_conf,
                source="calibrating",
            )

        # ── Determine status ──
        status_priority = {"Normal": 0, "Calibrating": 0, "Watch": 1, "Critical": 2}

        # Start from PSD classification
        _, psd_status = classify_vitals(psd_reading.heart_rate, psd_reading.respiration_rate)
        final_status = psd_status

        # CNN overrides if confident and more severe
        if cnn_conf >= CNN_CONFIDENCE_THRESHOLD:
            if status_priority.get(cnn_status, 0) > status_priority.get(final_status, 0):
                final_status = cnn_status

        # ── Build alert list ──
        alerts = list(psd_reading.alerts)

        if cnn_label and cnn_label != "Normal" and cnn_conf >= CNN_CONFIDENCE_THRESHOLD:
            cnn_msg = f"CNN: {cnn_label} detected (confidence {cnn_conf:.0%})"
            if cnn_msg not in alerts:
                alerts.insert(0, cnn_msg)

        # ── Fused confidence: weighted geometric mean ──
        if psd_conf > 0 and cnn_conf > 0:
            fused_conf = float(np.sqrt(psd_conf * cnn_conf))
            source = "fused"
        elif psd_conf >= PSD_CONFIDENCE_THRESHOLD:
            fused_conf = psd_conf
            source = "psd"
        else:
            fused_conf = cnn_conf
            source = "cnn"

        return FusedReading(
            heart_rate=psd_reading.heart_rate,
            respiration_rate=psd_reading.respiration_rate,
            skin_tone_index=psd_reading.skin_tone_index,
            confidence=round(fused_conf, 2),
            status=final_status,
            alerts=alerts,
            cnn_label=cnn_label,
            cnn_confidence=cnn_conf,
            psd_confidence=psd_conf,
            source=source,
        )
