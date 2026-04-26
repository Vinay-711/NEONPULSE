"""
NeoPulse AI — Eulerian Video Magnification (EVM) Core Engine
=============================================================
Implements the Wadhwa et al. (MIT 2013) EVM algorithm adapted for
non-contact neonatal vital extraction:
  - Pulse (rPPG):     bandpass 0.75–3.5 Hz  (~45–210 bpm)
  - Respiration:      bandpass 0.1–0.6 Hz   (~6–36 breaths/min)

Pipeline:
  VideoReader → Spatial Pyramid → Temporal Bandpass → Magnify → VitalExtractor
"""

import cv2
import numpy as np
from scipy.signal import butter, filtfilt, welch, find_peaks
from collections import deque
from typing import Optional


# ---------------------------------------------------------------------------
# Spatial filtering — Laplacian pyramid
# ---------------------------------------------------------------------------

def build_laplacian_pyramid(frame: np.ndarray, levels: int = 4) -> list[np.ndarray]:
    """Decompose a frame into a Laplacian pyramid."""
    pyramid = []
    current = frame.astype(np.float32)
    for _ in range(levels):
        blurred = cv2.pyrDown(current)
        expanded = cv2.pyrUp(blurred, dstsize=(current.shape[1], current.shape[0]))
        laplacian = current - expanded
        pyramid.append(laplacian)
        current = blurred
    pyramid.append(current)  # residual (Gaussian)
    return pyramid


def reconstruct_from_pyramid(pyramid: list[np.ndarray]) -> np.ndarray:
    """Collapse a Laplacian pyramid back to a full-resolution frame."""
    result = pyramid[-1]
    for level in reversed(pyramid[:-1]):
        result = cv2.pyrUp(result, dstsize=(level.shape[1], level.shape[0]))
        result = result + level
    return result


# ---------------------------------------------------------------------------
# Temporal bandpass filter
# ---------------------------------------------------------------------------

def butter_bandpass(lowcut: float, highcut: float, fs: float, order: int = 3):
    """Design a Butterworth bandpass filter."""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = min(highcut / nyq, 0.99)
    b, a = butter(order, [low, high], btype='band')
    return b, a


def apply_temporal_filter(
    signal_buffer: np.ndarray,
    lowcut: float,
    highcut: float,
    fs: float,
    order: int = 3,
) -> np.ndarray:
    """
    Apply a zero-phase Butterworth bandpass filter along the time axis.
    signal_buffer shape: (T, H, W, C)
    Returns filtered buffer of same shape.
    """
    if signal_buffer.shape[0] < 9:
        return signal_buffer  # not enough frames yet
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    return filtfilt(b, a, signal_buffer, axis=0)


# ---------------------------------------------------------------------------
# EVM Processor
# ---------------------------------------------------------------------------

class EVMProcessor:
    """
    Full Eulerian Video Magnification processor.

    Accumulates frames, applies spatial + temporal filtering, and returns
    magnified frames for downstream vital extraction.

    Parameters
    ----------
    fps : float
        Camera frames per second (typically 30).
    pyramid_levels : int
        Depth of Laplacian pyramid. Level 2–3 is the key spatial band
        for skin rPPG signal (~1–2 cm resolution blobs at 30 fps).
    pulse_alpha : float
        Magnification factor for pulse band (color amplification).
    resp_alpha : float
        Magnification factor for respiration band (motion amplification).
    buffer_seconds : float
        Rolling window length in seconds for temporal filtering.
    """

    PULSE_LOW  = 0.75   # Hz — ~45 bpm (bradycardia threshold)
    PULSE_HIGH = 3.5    # Hz — ~210 bpm (tachycardia ceiling)
    RESP_LOW   = 0.10   # Hz — ~6 breaths/min
    RESP_HIGH  = 0.60   # Hz — ~36 breaths/min (tachypnea threshold)

    def __init__(
        self,
        fps: float = 30.0,
        pyramid_levels: int = 4,
        pulse_alpha: float = 50.0,
        resp_alpha: float = 10.0,
        buffer_seconds: float = 10.0,
        roi: Optional[tuple] = None,          # (x, y, w, h) or None for full frame
        work_size: tuple = (320, 240),         # resize for speed
    ):
        self.fps = fps
        self.pyramid_levels = pyramid_levels
        self.pulse_alpha = pulse_alpha
        self.resp_alpha = resp_alpha
        self.buffer_size = int(buffer_seconds * fps)
        self.roi = roi
        self.work_size = work_size

        # Rolling frame buffer (raw pyramid levels)
        self._frame_buffer: deque = deque(maxlen=self.buffer_size)
        # Extracted raw color channel signals over time
        self._green_signal: deque = deque(maxlen=self.buffer_size)
        self._motion_signal: deque = deque(maxlen=self.buffer_size)

        self._prev_gray: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_frame(self, frame_bgr: np.ndarray) -> dict:
        """
        Ingest one BGR frame. Returns a dict with:
          - 'magnified'      : magnified BGR frame (same size as input)
          - 'green_trace'    : current rolling green-channel mean (float)
          - 'motion_trace'   : current rolling motion magnitude (float)
          - 'pyramid'        : list of pyramid levels (for debugging)
        """
        # --- Crop to ROI if set ---
        orig_frame = frame_bgr.copy()
        if self.roi:
            x, y, w, h = self.roi
            frame_bgr = frame_bgr[y:y+h, x:x+w]

        # --- Resize for processing speed ---
        small = cv2.resize(frame_bgr, self.work_size)
        small_f = small.astype(np.float32) / 255.0

        # --- Extract green channel mean (rPPG proxy) ---
        green_mean = float(small_f[:, :, 1].mean())
        self._green_signal.append(green_mean)

        # --- Extract motion via optical flow on gray ---
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if self._prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self._prev_gray, gray, None,
                pyr_scale=0.5, levels=2, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
            )
            motion_mag = float(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2).mean())
        else:
            motion_mag = 0.0
        self._prev_gray = gray
        self._motion_signal.append(motion_mag)

        # --- Build Laplacian pyramid ---
        pyramid = build_laplacian_pyramid(small_f, self.pyramid_levels)
        self._frame_buffer.append(pyramid)

        # --- Magnify when we have enough frames ---
        magnified_small = small_f.copy()
        if len(self._frame_buffer) >= max(9, int(self.fps * 2)):
            magnified_small = self._magnify(small_f, pyramid)

        # --- Upscale magnified back to original frame size ---
        out_h, out_w = orig_frame.shape[:2]
        magnified_bgr = (np.clip(magnified_small, 0, 1) * 255).astype(np.uint8)
        magnified_bgr = cv2.resize(magnified_bgr, (out_w, out_h))

        # Paste back into original frame at ROI
        result_frame = orig_frame.copy()
        if self.roi:
            x, y, w, h = self.roi
            result_frame[y:y+h, x:x+w] = magnified_bgr
        else:
            result_frame = magnified_bgr

        return {
            "magnified": result_frame,
            "green_trace": green_mean,
            "motion_trace": motion_mag,
            "pyramid": pyramid,
            "buffer_fill": len(self._frame_buffer) / self.buffer_size,
        }

    @property
    def green_signal_array(self) -> np.ndarray:
        return np.array(self._green_signal)

    @property
    def motion_signal_array(self) -> np.ndarray:
        return np.array(self._motion_signal)

    # ------------------------------------------------------------------
    # Internal magnification
    # ------------------------------------------------------------------

    def _magnify(self, current_frame: np.ndarray, current_pyramid: list) -> np.ndarray:
        """
        Core EVM step: filter buffer temporally and amplify each pyramid level.
        Uses the lowest pyramid level (most spatially blurred) for color (pulse)
        and a mid-level for motion (respiration).
        """
        # Stack pyramid levels across time: shape (T, H, W, C)
        buf = list(self._frame_buffer)
        T = len(buf)

        # We'll magnify pyramid level 2 (color) and level 1 (motion)
        pulse_level = min(2, self.pyramid_levels - 1)
        resp_level  = min(1, self.pyramid_levels - 1)

        try:
            # --- Pulse band: color amplification ---
            color_stack = np.stack([b[pulse_level] for b in buf], axis=0)  # (T, H, W, C)
            color_filtered = apply_temporal_filter(
                color_stack, self.PULSE_LOW, self.PULSE_HIGH, self.fps
            )
            amplified_color = color_filtered[-1] * self.pulse_alpha

            # --- Respiration band: motion amplification ---
            motion_stack = np.stack([b[resp_level] for b in buf], axis=0)
            motion_filtered = apply_temporal_filter(
                motion_stack, self.RESP_LOW, self.RESP_HIGH, self.fps
            )
            amplified_motion = motion_filtered[-1] * self.resp_alpha

        except Exception:
            # Graceful degradation if filter fails (too few frames etc.)
            return current_frame

        # --- Reconstruct: inject amplification back into current pyramid ---
        mod_pyramid = list(current_pyramid)
        mod_pyramid[pulse_level] = mod_pyramid[pulse_level] + amplified_color
        mod_pyramid[resp_level]  = mod_pyramid[resp_level]  + amplified_motion

        return reconstruct_from_pyramid(mod_pyramid)
