"""
NeoPulse AI — Vital Sign Extractor
====================================
Converts raw EVM color/motion signals into clinical vital readings:
  - Heart rate (bpm) via rPPG green-channel frequency analysis
  - Respiration rate (breaths/min) via motion magnitude frequency analysis
  - Skin tone stability index (0–1)
  - Alert classification (Normal / Watch / Critical)

All calculations use Welch's power spectral density method, which is
robust to the short, noisy windows typical of non-contact monitoring.
"""

import numpy as np
from scipy.signal import welch, detrend, find_peaks, butter, filtfilt
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VitalReading:
    heart_rate: float          # bpm
    respiration_rate: float    # breaths/min
    skin_tone_index: float     # 0.0 – 1.0 (stability of color signal)
    confidence: float          # 0.0 – 1.0 (signal quality estimate)
    alerts: list[str] = field(default_factory=list)
    status: str = "Normal"     # "Normal" | "Watch" | "Critical"


# ---------------------------------------------------------------------------
# Neonatal reference ranges (AAP / WHO guidelines)
# ---------------------------------------------------------------------------

NEONATAL_RANGES = {
    "heart_rate": {
        "normal":   (100, 160),   # bpm
        "watch":    (90,  180),   # triggers Watch alert
        "critical": (80,  200),   # triggers Critical alert
    },
    "respiration_rate": {
        "normal":   (30, 60),     # breaths/min
        "watch":    (20, 70),
        "critical": (15, 80),
    },
}


# ---------------------------------------------------------------------------
# Frequency-domain vital extraction
# ---------------------------------------------------------------------------

def estimate_rate_from_psd(
    signal: np.ndarray,
    fs: float,
    freq_low: float,
    freq_high: float,
    min_samples: int = 60,
) -> tuple[float, float]:
    """
    Estimate a periodic rate (bpm or brpm) from a 1D signal using
    Welch's method on the detrended, windowed signal.

    Returns
    -------
    rate : float
        Estimated rate in cycles-per-minute (bpm or brpm).
    snr : float
        Signal-to-noise ratio of the dominant frequency peak (proxy for confidence).
    """
    if len(signal) < min_samples:
        return 0.0, 0.0

    # Detrend to remove DC drift (lighting changes, camera movement)
    s = detrend(signal)

    # Welch PSD — nperseg tuned for the expected signal length
    nperseg = min(len(s), 256)
    freqs, psd = welch(s, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)

    # Mask to target band
    mask = (freqs >= freq_low) & (freqs <= freq_high)
    if not mask.any():
        return 0.0, 0.0

    band_freqs = freqs[mask]
    band_psd   = psd[mask]

    # Dominant peak in band
    peak_idx = int(np.argmax(band_psd))
    peak_freq = band_freqs[peak_idx]
    peak_power = band_psd[peak_idx]

    # SNR: peak vs mean of rest of band
    rest_power = np.mean(np.delete(band_psd, peak_idx)) + 1e-10
    snr = peak_power / rest_power

    rate_per_min = peak_freq * 60.0
    return float(rate_per_min), float(snr)


def skin_tone_stability(green_signal: np.ndarray) -> float:
    """
    Estimate how stable (i.e., physiologically meaningful) the color
    signal is. High-frequency noise from motion artifacts → low score.
    Returns a value in [0, 1].
    """
    if len(green_signal) < 10:
        return 0.0
    normed = (green_signal - green_signal.mean()) / (green_signal.std() + 1e-8)
    # Coefficient of variation — lower = more stable
    cv = green_signal.std() / (green_signal.mean() + 1e-8)
    score = float(np.clip(1.0 - cv * 10, 0.0, 1.0))
    return round(score, 3)


def compute_confidence(hr_snr: float, rr_snr: float, n_frames: int, target_frames: int) -> float:
    """
    Aggregate confidence from signal quality and buffer fullness.
    """
    snr_score    = float(np.clip((hr_snr + rr_snr) / 2 / 10, 0, 1))
    fill_score   = float(np.clip(n_frames / target_frames, 0, 1))
    confidence   = 0.6 * snr_score + 0.4 * fill_score
    return round(confidence, 2)


# ---------------------------------------------------------------------------
# Alert classification
# ---------------------------------------------------------------------------

def classify_vitals(hr: float, rr: float) -> tuple[list[str], str]:
    """
    Apply neonatal reference ranges and return a list of alert strings
    and an overall status string.
    """
    alerts = []
    status_levels = {"Normal": 0, "Watch": 1, "Critical": 2}
    overall = "Normal"

    def check(name, value, ranges, unit):
        nonlocal overall
        if value <= 0:
            return
        n_lo, n_hi = ranges["normal"]
        w_lo, w_hi = ranges["watch"]
        c_lo, c_hi = ranges["critical"]

        in_normal   = n_lo <= value <= n_hi
        in_watch    = w_lo <= value <= w_hi
        in_critical = c_lo <= value <= c_hi

        if not in_critical:
            alerts.append(f"CRITICAL: {name} {value:.0f} {unit} — outside safe range ({c_lo}–{c_hi})")
            if status_levels[overall] < 2:
                overall = "Critical"
        elif not in_watch:
            alerts.append(f"CRITICAL: {name} {value:.0f} {unit} — outside watch range ({w_lo}–{w_hi})")
            if status_levels[overall] < 2:
                overall = "Critical"
        elif not in_normal:
            alerts.append(f"WATCH: {name} {value:.0f} {unit} — outside normal range ({n_lo}–{n_hi})")
            if status_levels[overall] < 1:
                overall = "Watch"

    check("Heart rate",       hr, NEONATAL_RANGES["heart_rate"],       "bpm")
    check("Respiration rate", rr, NEONATAL_RANGES["respiration_rate"], "brpm")

    # Specific named conditions
    if hr > 0 and hr > 160:
        alerts.append("Possible tachycardia — HR > 160 bpm")
    if hr > 0 and hr < 100:
        alerts.append("Possible bradycardia — HR < 100 bpm")
    if rr > 0 and rr > 60:
        alerts.append("Possible tachypnea — RR > 60 brpm")

    return alerts, overall


# ---------------------------------------------------------------------------
# VitalExtractor — main API
# ---------------------------------------------------------------------------

class VitalExtractor:
    """
    Wraps frequency analysis, confidence scoring, and alert classification.
    Feed it the rolling signal arrays from EVMProcessor.

    Usage
    -----
    extractor = VitalExtractor(fps=30.0)
    reading = extractor.extract(green_signal, motion_signal)
    print(reading.heart_rate, reading.status)
    """

    PULSE_LOW  = 0.75
    PULSE_HIGH = 3.5
    RESP_LOW   = 0.10
    RESP_HIGH  = 0.60

    def __init__(self, fps: float = 30.0, buffer_seconds: float = 10.0):
        self.fps = fps
        self.target_frames = int(fps * buffer_seconds)

    def extract(
        self,
        green_signal: np.ndarray,
        motion_signal: np.ndarray,
    ) -> VitalReading:
        """
        Run frequency analysis on latest signal buffers.
        Returns a VitalReading (zeroed-out values if insufficient data).
        """
        n = len(green_signal)

        hr, hr_snr = estimate_rate_from_psd(
            green_signal, self.fps, self.PULSE_LOW, self.PULSE_HIGH
        )
        rr, rr_snr = estimate_rate_from_psd(
            motion_signal, self.fps, self.RESP_LOW, self.RESP_HIGH
        )

        sti        = skin_tone_stability(green_signal)
        confidence = compute_confidence(hr_snr, rr_snr, n, self.target_frames)
        alerts, status = classify_vitals(hr, rr)

        return VitalReading(
            heart_rate=round(hr, 1),
            respiration_rate=round(rr, 1),
            skin_tone_index=sti,
            confidence=confidence,
            alerts=alerts,
            status=status,
        )
