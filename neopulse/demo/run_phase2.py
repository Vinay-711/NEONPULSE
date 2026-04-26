"""
NeoPulse AI — Live Demo Runner (Phase 2 — with CNN fusion)
============================================================
Runs the full EVM + PSD + CNN fusion pipeline.

Usage
-----
  python -m neopulse.demo.run_phase2                         # webcam
  python -m neopulse.demo.run_phase2 --video path/to/vid    # video file
  python -m neopulse.demo.run_phase2 --simulate             # synthetic demo
  python -m neopulse.demo.run_phase2 --simulate --no-cnn    # PSD only

Keyboard: Q=quit  R=reset  S=save
"""

import argparse, json, time, sys, os
import cv2, numpy as np

from neopulse.core.evm     import EVMProcessor
from neopulse.core.vitals  import VitalExtractor
from neopulse.alerts.manager import AlertManager
from neopulse.ml.fusion    import FusionEngine, FusedReading

FONT     = cv2.FONT_HERSHEY_SIMPLEX
C_OK     = (80, 200, 100)
C_WRN    = (0, 200, 220)
C_CRT    = (60,  60, 230)
C_CAL    = (180, 140, 60)
C_DIM    = (160, 160, 160)

STATUS_COLORS = {"Normal": C_OK, "Watch": C_WRN, "Critical": C_CRT,
                 "Calibrating": C_CAL}

def status_color(s):
    return STATUS_COLORS.get(s, C_DIM)

def source_badge_color(source):
    return {"psd": C_OK, "cnn": (180, 100, 220), "fused": (200, 180, 60),
            "calibrating": C_CAL}.get(source, C_DIM)


def draw_panel(frame, reading: FusedReading, fps_actual: float, buf_fill: float):
    h, w = frame.shape[:2]
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (270, h), (20, 20, 30), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)

    col = status_color(reading.status)
    y = 28

    cv2.putText(frame, "NeoPulse AI", (10, y), FONT, 0.62, (255,255,255), 1, cv2.LINE_AA)
    y += 22
    cv2.putText(frame, f"Status: {reading.status}", (10, y), FONT, 0.52, col, 1, cv2.LINE_AA)
    src_col = source_badge_color(reading.source)
    cv2.putText(frame, f"[{reading.source}]", (160, y), FONT, 0.38, src_col, 1, cv2.LINE_AA)
    y += 26
    cv2.line(frame, (10, y), (260, y), (80, 80, 80), 1); y += 16

    def vital_row(label, value, unit, lo, hi):
        nonlocal y
        c = C_OK if lo <= value <= hi else (C_CRT if value > 0 else C_DIM)
        cv2.putText(frame, label, (10, y), FONT, 0.38, C_DIM, 1, cv2.LINE_AA); y += 16
        val_str = f"{value:.0f} {unit}" if value > 0 else "---"
        cv2.putText(frame, val_str, (10, y), FONT, 0.62, c, 2, cv2.LINE_AA)
        cv2.putText(frame, f"({lo}-{hi})", (140, y), FONT, 0.35, C_DIM, 1, cv2.LINE_AA); y += 26

    vital_row("Heart Rate",       reading.heart_rate,       "bpm",  100, 160)
    vital_row("Respiration Rate", reading.respiration_rate, "brpm",  30,  60)

    # CNN output row
    if reading.cnn_label:
        cv2.putText(frame, "CNN verdict", (10, y), FONT, 0.38, C_DIM, 1, cv2.LINE_AA); y += 16
        cnn_col = C_OK if reading.cnn_label == "Normal" else C_WRN
        cv2.putText(frame, f"{reading.cnn_label} {reading.cnn_confidence:.0%}",
                    (10, y), FONT, 0.52, cnn_col, 1, cv2.LINE_AA); y += 24

    # Bars
    for bar_label, val, bar_col in [
        ("Confidence", reading.confidence, C_OK),
        ("Buffer",     buf_fill,           (100, 100, 180)),
    ]:
        cv2.putText(frame, bar_label, (10, y), FONT, 0.38, C_DIM, 1, cv2.LINE_AA); y += 14
        bw = int(val * 220)
        cv2.rectangle(frame, (10, y), (230, y+8), (60,60,60), -1)
        cv2.rectangle(frame, (10, y), (10+bw, y+8), bar_col, -1)
        y += 14

    cv2.line(frame, (10, y+2), (260, y+2), (80,80,80), 1); y += 14
    cv2.putText(frame, f"FPS: {fps_actual:.1f}    Q:quit R:reset S:save",
                (10, y), FONT, 0.34, C_DIM, 1, cv2.LINE_AA)

    if reading.alerts:
        msg = reading.alerts[0][:58]
        bcol = (30,30,160) if reading.status == "Critical" else (30,80,130)
        cv2.rectangle(frame, (0, h-34), (w, h), bcol, -1)
        cv2.putText(frame, msg, (8, h-10), FONT, 0.44, (255,255,255), 1, cv2.LINE_AA)


def draw_waveform(frame, signal, region, color, label):
    x, y, rw, rh = region
    cv2.rectangle(frame, (x, y), (x+rw, y+rh), (30,30,40), -1)
    if len(signal) < 4:
        return
    s = signal[-rw:]
    if s.std() < 1e-8:
        return
    norm = (s - s.min()) / (s.max()-s.min()+1e-8)
    pts  = [(x+i, y+rh-int(v*(rh-4))-2) for i,v in enumerate(norm)]
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i-1], pts[i], color, 1, cv2.LINE_AA)
    cv2.putText(frame, label, (x+4, y+14), FONT, 0.32, (140,140,140), 1, cv2.LINE_AA)


def generate_synthetic_frame(t, fps=30, w=640, h=480):
    frame = np.ones((h, w, 3), dtype=np.uint8) * 180
    pulse = np.sin(2*np.pi*2.0*t)*6
    drift = int(np.sin(2*np.pi*0.5*t)*8)
    color = [int(np.clip(120, 0, 255)),
             int(np.clip(140+pulse, 0, 255)),
             int(np.clip(160, 0, 255))]
    cy = h//2 + drift
    cv2.ellipse(frame, (w//2, cy), (140, 100), 0, 0, 360, color, -1)
    noise = np.random.randint(-3, 4, frame.shape, dtype=np.int8)
    return np.clip(frame.astype(np.int16)+noise, 0, 255).astype(np.uint8)


def run(source=0, simulate=False, use_cnn=True):
    fps = 30.0
    evm       = EVMProcessor(fps=fps, pyramid_levels=4, pulse_alpha=50.0, resp_alpha=10.0)
    extractor = VitalExtractor(fps=fps)
    alert_mgr = AlertManager()
    fusion    = FusionEngine()

    # Try to load CNN classifier
    cnn_buf = None
    if use_cnn:
        try:
            from neopulse.ml.classifier import TFLiteClassifier, SlidingWindowBuffer, MODEL_PATH
            if MODEL_PATH.exists():
                clf = TFLiteClassifier(MODEL_PATH)
                from neopulse.ml.classifier import SlidingWindowBuffer
                cnn_buf = SlidingWindowBuffer(clf, stride=15)
                print(f"[NeoPulse] CNN classifier loaded: {MODEL_PATH}")
            else:
                print("[NeoPulse] No model.tflite found — running PSD-only mode.")
                print("           Train with: python -m neopulse.ml.classifier --train")
        except Exception as e:
            print(f"[NeoPulse] CNN unavailable ({e}) — PSD-only mode.")

    if not simulate:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"[NeoPulse] Cannot open: {source}"); return
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        evm.fps = fps

    vitals_log = []
    frame_count = 0
    t0 = time.time()
    last_extract = 0.0
    t_sim = 0.0

    cnn_label, cnn_conf, cnn_probs = None, 0.0, None
    psd_reading = extractor.extract(np.array([0.5]), np.array([0.01]))
    fused = fusion.fuse(psd_reading, None, 0.0)

    print("[NeoPulse] Starting. Press Q to quit.")

    while True:
        if simulate:
            frame = generate_synthetic_frame(t_sim, fps)
            t_sim += 1.0/fps
            time.sleep(max(0, 1.0/fps - 0.002))
        else:
            ret, frame = cap.read()
            if not ret:
                break

        frame_count += 1
        now = time.time()
        fps_actual = frame_count / max(now - t0, 0.001)

        result = evm.process_frame(frame)
        display = result["magnified"].copy()

        g_val = result["green_trace"]
        m_val = result["motion_trace"]

        # CNN sliding window
        if cnn_buf is not None:
            cnn_result = cnn_buf.push(g_val, m_val)
            if cnn_result:
                cnn_label, cnn_conf, cnn_probs = cnn_result

        # Extract vitals + fuse every 1s
        if now - last_extract >= 1.0:
            last_extract = now
            psd_reading = extractor.extract(evm.green_signal_array, evm.motion_signal_array)
            fused = fusion.fuse(psd_reading, cnn_label, cnn_conf, cnn_probs)
            alert_mgr.process(fused.to_vital_reading())

        # Waveforms
        h_fr, w_fr = display.shape[:2]
        g_arr = evm.green_signal_array * 1000
        m_arr = evm.motion_signal_array * 1000
        draw_waveform(display, g_arr, (275, h_fr-90, w_fr-280, 40), C_OK,  "rPPG (green channel)")
        draw_waveform(display, m_arr, (275, h_fr-44, w_fr-280, 40), C_WRN, "Motion (respiration)")

        draw_panel(display, fused, fps_actual, result["buffer_fill"])
        cv2.imshow("NeoPulse AI — Phase 2", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            evm = EVMProcessor(fps=fps)
            print("[NeoPulse] Buffer reset.")
        elif key == ord('s'):
            entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "heart_rate": fused.heart_rate, "respiration_rate": fused.respiration_rate,
                "status": fused.status, "source": fused.source,
                "cnn_label": fused.cnn_label, "cnn_confidence": fused.cnn_confidence,
                "alerts": fused.alerts,
            }
            vitals_log.append(entry)
            with open("vitals_log_p2.json", "w") as f:
                json.dump(vitals_log, f, indent=2)
            print(f"[NeoPulse] Saved reading ({len(vitals_log)} total)")

    if not simulate:
        cap.release()
    cv2.destroyAllWindows()
    print(f"\n[NeoPulse] Session ended. {frame_count} frames processed.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video",    type=str,  default=None)
    p.add_argument("--camera",   type=int,  default=0)
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--no-cnn",   action="store_true")
    args = p.parse_args()

    if args.simulate:
        run(simulate=True, use_cnn=not args.no_cnn)
    elif args.video:
        run(source=args.video, use_cnn=not args.no_cnn)
    else:
        run(source=args.camera, use_cnn=not args.no_cnn)
