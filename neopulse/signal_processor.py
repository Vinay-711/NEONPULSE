import numpy as np
from scipy.signal import find_peaks, savgol_filter
from dataclasses import dataclass
from typing import List, Tuple
import unittest

@dataclass
class VitalSigns:
    hr_bpm: float
    rr_bpm: float
    hr_confidence: float
    rr_confidence: float
    timestamp: float

class SignalProcessor:
    def __init__(self, fps: float = 30.0, window_seconds: float = 10.0):
        self.fps = fps
        self.window_seconds = window_seconds
        
    def estimate_rate(self, signal: np.ndarray, is_hr: bool) -> Tuple[float, float]:
        """
        Estimates the rate (BPM) from a 1D EVM signal using Savitzky-Golay smoothing 
        and adaptive prominence peak detection.
        """
        if len(signal) < 10:
            return 0.0, 0.0
            
        # 1. Apply Savitzky-Golay smoothing filter
        # Window length must be odd and ideally around 0.5 to 1 second of data
        window_length = int(self.fps * 0.5) 
        if window_length % 2 == 0:
            window_length += 1
            
        if window_length > len(signal):
            window_length = len(signal) - 1 if (len(signal) - 1) % 2 != 0 else len(signal) - 2
            
        if window_length >= 3:
            filtered_signal = savgol_filter(signal, window_length, polyorder=2)
        else:
            filtered_signal = signal
            
        # 2. Adaptive prominence thresholding
        # Set prominence to 50% of the standard deviation to filter out low-amplitude noise
        prominence = 0.5 * np.std(filtered_signal)
        
        # 3. Determine distance constraint based on physiological limits
        # HR bounds: up to 180 BPM (3.0 Hz) -> min distance is ~0.33 sec
        # RR bounds: up to 48 breaths/min (0.8 Hz) -> min distance is ~1.25 sec
        # We multiply by 0.8 as a safety factor so we don't miss slightly early peaks
        if is_hr:
            distance = max(1, int((1.0 / 3.0) * self.fps * 0.8))
        else:
            distance = max(1, int((1.0 / 0.8) * self.fps * 0.8))
            
        # 4. Find Peaks
        peaks, _ = find_peaks(filtered_signal, prominence=prominence, distance=distance)
        
        if len(peaks) < 2:
            return 0.0, 0.0
            
        # 5. Calculate Rates and Confidence
        intervals = np.diff(peaks) / self.fps # Convert intervals to seconds
        mean_interval = np.mean(intervals)
        
        if mean_interval == 0:
            return 0.0, 0.0
            
        rate_bpm = (1.0 / mean_interval) * 60.0
        
        # Confidence calculation based on rhythm regularity
        # Coefficient of Variation (CV) = Standard Deviation / Mean
        # A perfect sine wave has CV = 0. We penalize high variance.
        cv = np.std(intervals) / mean_interval
        
        # Scale confidence: CV of 0 -> 1.0 confidence, CV >= 0.3 -> 0.0 confidence
        confidence = max(0.0, 1.0 - (cv / 0.3))
        
        return rate_bpm, confidence

    def process_window(self, hr_signal: List[float], rr_signal: List[float], timestamps: List[float]) -> VitalSigns:
        """
        Processes a rolling window of EVM outputs to compute heart rate and respiratory rate.
        Expected to be called on a window representing the last 10 seconds.
        """
        hr_array = np.array(hr_signal)
        rr_array = np.array(rr_signal)
        
        hr_bpm, hr_conf = self.estimate_rate(hr_array, is_hr=True)
        rr_bpm, rr_conf = self.estimate_rate(rr_array, is_hr=False)
        
        current_time = timestamps[-1] if len(timestamps) > 0 else 0.0
        
        return VitalSigns(
            hr_bpm=round(hr_bpm, 2),
            rr_bpm=round(rr_bpm, 2),
            hr_confidence=round(hr_conf, 3),
            rr_confidence=round(rr_conf, 3),
            timestamp=current_time
        )

# ==========================================
# UNIT TESTS
# ==========================================
class TestSignalProcessor(unittest.TestCase):
    def setUp(self):
        self.fps = 30.0
        self.duration = 10.0 # 10 seconds rolling window
        self.t = np.linspace(0, self.duration, int(self.fps * self.duration), endpoint=False)
        self.processor = SignalProcessor(fps=self.fps, window_seconds=self.duration)
        
    def test_heart_rate_estimation_clean_sine(self):
        # Synthetic HR signal: 1.5 Hz = 90 BPM
        target_hz = 1.5
        hr_signal = np.sin(2 * np.pi * target_hz * self.t) + 0.05 * np.random.randn(len(self.t))
        rr_signal = np.zeros_like(self.t)
        
        vitals = self.processor.process_window(hr_signal.tolist(), rr_signal.tolist(), self.t.tolist())
        
        # Allow small margin of error due to discretization
        self.assertTrue(87 <= vitals.hr_bpm <= 93, f"Expected ~90 BPM, got {vitals.hr_bpm}")
        self.assertGreater(vitals.hr_confidence, 0.8, "Confidence should be high for regular sine wave")
        
    def test_respiratory_rate_estimation_clean_sine(self):
        # Synthetic RR signal: 0.3 Hz = 18 Breaths/Min
        target_hz = 0.3
        hr_signal = np.zeros_like(self.t)
        rr_signal = np.sin(2 * np.pi * target_hz * self.t) + 0.05 * np.random.randn(len(self.t))
        
        vitals = self.processor.process_window(hr_signal.tolist(), rr_signal.tolist(), self.t.tolist())
        
        self.assertTrue(16 <= vitals.rr_bpm <= 20, f"Expected ~18 BPM, got {vitals.rr_bpm}")
        self.assertGreater(vitals.rr_confidence, 0.8, "Confidence should be high for regular sine wave")
        
    def test_noisy_signal_rejection(self):
        # Pure noise should result in low confidence
        hr_signal = np.random.randn(len(self.t))
        rr_signal = np.random.randn(len(self.t))
        
        vitals = self.processor.process_window(hr_signal.tolist(), rr_signal.tolist(), self.t.tolist())
        
        self.assertLess(vitals.hr_confidence, 0.5, "Confidence should be low for pure noise")
        self.assertLess(vitals.rr_confidence, 0.5, "Confidence should be low for pure noise")

if __name__ == '__main__':
    unittest.main()
