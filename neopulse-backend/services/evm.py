import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks

def extract_rppg_signal(frames: list[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.array([])
    
    H, W, _ = frames[0].shape
    
    # Face ROI: centre 40% width, top 30% height
    x1 = int(W * 0.3)
    x2 = int(W * 0.7)
    y1 = 0
    y2 = int(H * 0.3)
    
    signal = []
    for frame in frames:
        roi = frame[y1:y2, x1:x2]
        # Ensure ROI exists
        if roi.size == 0:
            signal.append(0.0)
            continue
            
        r = roi[:, :, 0].astype(np.float32)
        g = roi[:, :, 1].astype(np.float32)
        b = roi[:, :, 2].astype(np.float32)
        
        rppg = np.mean(g - 0.5 * r - 0.5 * b)
        signal.append(rppg)
        
    return np.array(signal)

def extract_motion_signal(frames: list[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.array([])
        
    signal = []
    prev_roi = None

    for frame in frames:
        # Recompute the ROI when frame dimensions change.
        height, width, _ = frame.shape
        x1, x2 = int(width * 0.2), int(width * 0.8)
        y1, y2 = int(height * 0.35), int(height * 0.65)
        roi = frame[y1:y2, x1:x2].astype(np.float32)
        if roi.size == 0:
            signal.append(0.0)
            prev_roi = None
            continue

        if prev_roi is not None and roi.shape == prev_roi.shape:
            signal.append(np.mean(np.abs(roi - prev_roi)))
        else:
            signal.append(0.0)
        prev_roi = roi

    return np.array(signal)

def bandpass_filter(signal: np.ndarray, fs: float, low_hz: float, high_hz: float) -> np.ndarray:
    if len(signal) < 15:
        return signal
    nyq = 0.5 * fs
    low = low_hz / nyq
    high = high_hz / nyq
    sos = butter(4, [low, high], btype='bandpass', output='sos')
    padlen = min(39, len(signal) - 1)
    return sosfiltfilt(sos, signal, padlen=padlen)

def compute_confidence(intervals: np.ndarray) -> float:
    if len(intervals) < 2:
        return 0.0
    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    return float(max(0.0, min(1.0, 1.0 - (std_interval / mean_interval))) if mean_interval > 0 else 0.0)

def estimate_heart_rate(signal: np.ndarray, fs: float) -> tuple[float, float]:
    if len(signal) == 0:
        return 0.0, 0.0
        
    if np.std(signal) > 0:
        norm_sig = (signal - np.mean(signal)) / np.std(signal)
    else:
        norm_sig = signal
        
    peaks, properties = find_peaks(norm_sig, prominence=0.1, distance=fs*0.4)
    
    if len(peaks) < 2:
        return 0.0, 0.0
        
    intervals = np.diff(peaks) / fs
    mean_interval = np.mean(intervals)
    hr_bpm = 60.0 / mean_interval if mean_interval > 0 else 0.0
    
    confidence = compute_confidence(intervals)
    
    return float(hr_bpm), float(confidence)

def estimate_breathing_rate(signal: np.ndarray, fs: float) -> tuple[float, float]:
    if len(signal) == 0:
        return 0.0, 0.0
        
    if np.std(signal) > 0:
        norm_sig = (signal - np.mean(signal)) / np.std(signal)
    else:
        norm_sig = signal
        
    peaks, properties = find_peaks(norm_sig, prominence=0.05, distance=fs*0.8)
    
    if len(peaks) < 2:
        return 0.0, 0.0
        
    intervals = np.diff(peaks) / fs
    mean_interval = np.mean(intervals)
    rr_bpm = 60.0 / mean_interval if mean_interval > 0 else 0.0
    
    confidence = compute_confidence(intervals)
    
    return float(rr_bpm), float(confidence)
