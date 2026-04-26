import numpy as np
import cv2
import scipy.signal as signal
import matplotlib.pyplot as plt
import time

class EulerianVideoMagnifier:
    """
    Eulerian Video Magnification
    Targeting: Mobile deployment via TFLite
    Note: For true TFLite conversion, the sliding window `filtfilt` over 150 frames 
    would ideally be converted to an online IIR filter carrying states (using `lfilter` and `zi`),
    but we use a 150-frame buffer here to strictly follow the sliding window approach.
    """
    def __init__(self, fps=30, window_size=150, levels=4):
        self.fps = fps
        self.window_size = window_size
        self.levels = levels
        
        # Buffer for Y channel pyramids (List of deques/lists, one for each pyramid level)
        self.pyramid_buffers = [[] for _ in range(levels + 1)]
        
        # Keep track of original I and Q channels for the current frame
        self.current_i = None
        self.current_q = None
        self.current_y = None
        
        # 1D output signals and timestamps
        self.hr_signal = []
        self.rr_signal = []
        self.timestamps = []
        self.start_time = None
        
        # Butterworth filters setup
        nyq = 0.5 * fps
        # Heartbeat (HR): 0.8 - 3.0 Hz
        self.hr_b, self.hr_a = signal.butter(2, [0.8 / nyq, 3.0 / nyq], btype='bandpass')
        # Respiratory (RR): 0.1 - 0.8 Hz
        self.rr_b, self.rr_a = signal.butter(2, [0.1 / nyq, 0.8 / nyq], btype='bandpass')

    def rgb2yiq(self, rgb):
        """1. Convert frame to YIQ color space"""
        yiq_from_rgb = np.array([[0.299, 0.587, 0.114],
                                 [0.59590059, -0.27415583, -0.32174476],
                                 [0.21153661, -0.52273617, 0.31119955]])
        return np.dot(rgb, yiq_from_rgb.T.copy())

    def yiq2rgb(self, yiq):
        rgb_from_yiq = np.array([[1.0, 0.956, 0.621],
                                 [1.0, -0.272, -0.647],
                                 [1.0, -1.106, 1.703]])
        return np.dot(yiq, rgb_from_yiq.T.copy())

    def build_laplacian_pyramid(self, img):
        """2. Build a 4-level Laplacian spatial pyramid"""
        pyramid = []
        current = img.copy()
        for _ in range(self.levels):
            down = cv2.pyrDown(current)
            up = cv2.pyrUp(down, dstsize=(current.shape[1], current.shape[0]))
            lap = current - up
            pyramid.append(lap)
            current = down
        pyramid.append(current) # Top of pyramid
        return pyramid

    def collapse_laplacian_pyramid(self, pyramid):
        """5. Collapse pyramid back into a single image"""
        current = pyramid[-1]
        for i in range(len(pyramid)-2, -1, -1):
            up = cv2.pyrUp(current, dstsize=(pyramid[i].shape[1], pyramid[i].shape[0]))
            current = up + pyramid[i]
        return current

    def process_frame(self, frame_bgr):
        """
        Process a single BGR frame, buffer it, apply EVM if buffer is full,
        and yield the extracted signals.
        """
        if self.start_time is None:
            self.start_time = time.time()
            
        # Convert BGR -> RGB -> YIQ
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        frame_yiq = self.rgb2yiq(frame_rgb)
        
        # Only operate on the Y channel
        y, i_ch, q_ch = frame_yiq[:, :, 0], frame_yiq[:, :, 1], frame_yiq[:, :, 2]
        
        self.current_i = i_ch
        self.current_q = q_ch
        self.current_y = y
        
        # Build Laplacian pyramid on Y channel
        pyramid = self.build_laplacian_pyramid(y)
        
        for lvl in range(self.levels + 1):
            self.pyramid_buffers[lvl].append(pyramid[lvl])
            # Maintain sliding window of 150 frames
            if len(self.pyramid_buffers[lvl]) > self.window_size:
                self.pyramid_buffers[lvl].pop(0)
                
        # If we don't have enough frames to fill the sliding window, skip filtering
        if len(self.pyramid_buffers[0]) < self.window_size:
            return frame_bgr, 0.0, 0.0
            
        hr_pyramid_filtered = []
        rr_pyramid_filtered = []
        
        # 3. Apply Butterworth bandpass filter over the 150-frame sliding window
        for lvl in range(self.levels + 1):
            data = np.stack(self.pyramid_buffers[lvl], axis=0) # shape (150, H, W)
            
            # Apply filter along time axis (axis 0)
            # filtfilt is zero-phase, applying the filter forward and backward
            hr_filtered = signal.filtfilt(self.hr_b, self.hr_a, data, axis=0)
            rr_filtered = signal.filtfilt(self.rr_b, self.rr_a, data, axis=0)
            
            # 4. Amplify filtered signals
            # alpha=50 for HR, alpha=20 for RR
            hr_amp = hr_filtered[-1] * 50.0
            rr_amp = rr_filtered[-1] * 20.0
            
            hr_pyramid_filtered.append(hr_amp)
            rr_pyramid_filtered.append(rr_amp)
            
        # Collapse amplified pyramids
        hr_magnified_y = self.collapse_laplacian_pyramid(hr_pyramid_filtered)
        rr_magnified_y = self.collapse_laplacian_pyramid(rr_pyramid_filtered)
        
        # 5. Add back to original Y channel
        hr_y_out = self.current_y + hr_magnified_y
        # rr_y_out = self.current_y + rr_magnified_y # If we wanted RR visual output
        
        # Extract 1D time-series by taking the spatial mean of the magnified isolated motion
        current_hr_signal = np.mean(hr_magnified_y)
        current_rr_signal = np.mean(rr_magnified_y)
        
        t = time.time() - self.start_time
        self.timestamps.append(t)
        self.hr_signal.append(current_hr_signal)
        self.rr_signal.append(current_rr_signal)
        
        # Reconstruct final magnified RGB/BGR frame for visual validation (HR as an example)
        hr_yiq_out = np.stack([hr_y_out, self.current_i, self.current_q], axis=-1)
        hr_rgb_out = self.yiq2rgb(hr_yiq_out)
        hr_rgb_out = np.clip(hr_rgb_out, 0, 1)
        hr_bgr_out = cv2.cvtColor((hr_rgb_out * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        
        return hr_bgr_out, current_hr_signal, current_rr_signal

    def plot_signals(self):
        """Visualization function to plot the HR and RR time-series signals."""
        if not self.timestamps:
            print("No signals to plot yet. Process at least 150 frames first.")
            return
            
        plt.figure(figsize=(14, 7))
        
        plt.subplot(2, 1, 1)
        plt.plot(self.timestamps, self.hr_signal, color='#ff4d4d', linewidth=2, label='HR Signal (0.8-3.0 Hz)')
        plt.title('Eulerian Video Magnification - Extracted Signals', fontsize=14)
        plt.ylabel('Amplitude', fontsize=12)
        plt.legend(loc='upper right')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.subplot(2, 1, 2)
        plt.plot(self.timestamps, self.rr_signal, color='#4d94ff', linewidth=2, label='RR Signal (0.1-0.8 Hz)')
        plt.xlabel('Time (seconds)', fontsize=12)
        plt.ylabel('Amplitude', fontsize=12)
        plt.legend(loc='upper right')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.show()

# Example Usage:
if __name__ == "__main__":
    evm = EulerianVideoMagnifier(fps=30, window_size=150, levels=4)
    print("Initialized EVM Pipeline. Processing dummy frames...")
    
    # Simulating a video stream
    for i in range(160): # 150 for buffer + 10 for signal
        dummy_frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        _, hr_val, rr_val = evm.process_frame(dummy_frame)
        
    print("Done. Showing visualization...")
    evm.plot_signals()
