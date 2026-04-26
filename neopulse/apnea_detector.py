import collections
from dataclasses import dataclass
from typing import Optional

@dataclass
class ApneaEvent:
    duration_sec: float
    start_time: float
    confidence: float

class RuleBasedApneaDetector:
    """
    Lightweight rule-based Apnea Detector designed to run in parallel with the ML model.
    Monitors the RR signal envelope. If the amplitude drops below 15% of the 30-second 
    rolling mean for >10 consecutive seconds, it emits an EMERGENCY ApneaEvent.
    """
    def __init__(self, baseline_window_sec: float = 30.0, drop_threshold_ratio: float = 0.15, 
                 apnea_duration_sec: float = 10.0, debounce_sec: float = 5.0):
        self.baseline_window_sec = baseline_window_sec
        self.drop_threshold_ratio = drop_threshold_ratio
        self.apnea_duration_sec = apnea_duration_sec
        self.debounce_sec = debounce_sec
        
        # Buffer to maintain rolling 30-second mean
        self.history = collections.deque()
        self.history_sum = 0.0
        
        # State tracking
        self.apnea_start_time = None
        self.frozen_threshold = 0.0
        self.last_alert_time = -float('inf')
        
    def process_frame(self, signal_value: float, timestamp: float) -> Optional[ApneaEvent]:
        # EVM signals are bandpassed (zero-centered), so we look at the absolute amplitude envelope
        amp = abs(signal_value)
        
        # 1. Update 30-second rolling baseline
        self.history.append((timestamp, amp))
        self.history_sum += amp
        
        while self.history and (timestamp - self.history[0][0]) > self.baseline_window_sec:
            old_ts, old_amp = self.history.popleft()
            self.history_sum -= old_amp
            
        rolling_mean = self.history_sum / len(self.history) if self.history else 0.0
        
        # 2. Threshold determination
        # Freeze the threshold when an apnea event is developing so the baseline 
        # doesn't artificially drop to zero and cancel the emergency alert.
        if self.apnea_start_time is not None:
            active_threshold = self.frozen_threshold
        else:
            active_threshold = self.drop_threshold_ratio * rolling_mean
            
        # 3. Drop Evaluation
        if amp < active_threshold:
            # Drop detected, initialize candidate tracking
            if self.apnea_start_time is None:
                self.apnea_start_time = timestamp
                self.frozen_threshold = active_threshold
                
            current_duration = timestamp - self.apnea_start_time
            
            # 4. Trigger logic
            if current_duration >= self.apnea_duration_sec:
                # 5. Debounce check
                if (timestamp - self.last_alert_time) >= self.debounce_sec:
                    self.last_alert_time = timestamp
                    
                    # Calculate confidence based on how severe the drop is (rule-based)
                    if self.frozen_threshold == 0.0:
                        confidence = 1.0
                    else:
                        # Closer to 0 amp means closer to 1.0 confidence
                        confidence = min(1.0, 1.0 - (amp / self.frozen_threshold))
                    
                    # Immediately emit the event (bypasses ML scoring in external orchestrator)
                    return ApneaEvent(
                        duration_sec=round(current_duration, 2),
                        start_time=round(self.apnea_start_time, 2),
                        confidence=round(confidence, 3)
                    )
        else:
            # Signal recovered above threshold, cancel candidate state
            self.apnea_start_time = None
            self.frozen_threshold = 0.0
            
        return None
