# NeoPulse AI 🩺
### Non-contact neonatal vital monitoring via Eulerian Video Magnification

> Point a smartphone camera at a sleeping infant. Get continuous heart rate and
> respiration rate — no wearables, no hardware, no barriers to access.

---

## How it works

```
Smartphone camera
      │
      ▼
┌─────────────────────────────────────────┐
│  EVMProcessor  (core/evm.py)            │
│  1. Resize frame → 320×240              │
│  2. Build Laplacian pyramid (4 levels)  │
│  3. Rolling 10s frame buffer            │
│  4. Temporal bandpass filter:           │
│     • Pulse band  0.75–3.5 Hz           │
│     • Resp  band  0.10–0.60 Hz          │
│  5. Amplify filtered signal:            │
│     • pulse_alpha = 50× (color)         │
│     • resp_alpha  = 10× (motion)        │
│  6. Reconstruct magnified frame         │
└───────────────┬─────────────────────────┘
                │  green_signal[]  motion_signal[]
                ▼
┌─────────────────────────────────────────┐
│  VitalExtractor  (core/vitals.py)       │
│  Welch PSD → dominant frequency → bpm  │
│  Heart rate:       green channel        │
│  Respiration rate: optical flow mag     │
│  Skin tone index:  color stability      │
│  Confidence:       SNR × buffer fill    │
└───────────────┬─────────────────────────┘
                │  VitalReading
                ▼
┌─────────────────────────────────────────┐
│  AlertManager  (alerts/manager.py)      │
│  AAP/WHO neonatal reference ranges      │
│  Dedup + cooldown (30s default)         │
│  Escalation: Watch 60s → Critical       │
│  Backends: console / SMS / FCM push     │
└─────────────────────────────────────────┘
```

**Key science**: EVM (Wadhwa et al., MIT SIGGRAPH 2013) amplifies pixel
color changes by 50× in the pulse frequency band — making the subtle
hemoglobin-driven "flush" visible enough for frequency analysis.

---

## Setup

```bash
git clone <repo>
cd neopulse
pip install -r requirements.txt
```

Minimum Python: **3.10**

---

## Run the demo

```bash
# Webcam (default)
python -m neopulse.demo.run

# Video file
python -m neopulse.demo.run --video baby_clip.mp4

# Synthetic signal — no camera needed (great for hackathon demo)
python -m neopulse.demo.run --simulate
```

**Keyboard shortcuts during live view:**

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `R` | Reset signal buffer |
| `S` | Save current reading to `vitals_log.json` |

---

## Run the test suite

```bash
python -m neopulse.tests.test_pipeline
```

Expected output:
```
Test 1: EVM processes 300 frames without exception ... PASS
Test 2: Vital extraction within tolerance ...
   HR:  estimated=119.5 bpm  truth=120 bpm  error=0.5  PASS
   RR:  estimated=30.2 brpm  truth=30 brpm  error=0.2  PASS
   Confidence: 0.74  Status: Normal  PASS
Test 3: No alerts emitted for normal vitals ... PASS
Test 4: Alert emitted for bradycardia ... PASS
Test 5: Watch alert emitted for tachypnea ... PASS
Test 6: classify_vitals returns correct categories ... PASS

Benchmark: EVM throughput ... ~45 frames/sec  PASS
```

---

## Clinical reference ranges

| Vital | Normal | Watch | Critical |
|-------|--------|-------|----------|
| Heart rate | 100–160 bpm | 90–180 bpm | 80–200 bpm |
| Respiration | 30–60 brpm | 20–70 brpm | 15–80 brpm |

Source: American Academy of Pediatrics (AAP) neonatal guidelines.

Named conditions detected:
- **Tachycardia** — HR > 160 bpm
- **Bradycardia** — HR < 100 bpm
- **Tachypnea**  — RR > 60 brpm

---

## Project structure

```
neopulse/
├── core/
│   ├── evm.py          # Eulerian Video Magnification engine
│   └── vitals.py       # Frequency analysis + alert classification
├── alerts/
│   └── manager.py      # Alert routing, throttling, escalation
├── demo/
│   └── run.py          # Live demo with OpenCV overlay
├── tests/
│   └── test_pipeline.py  # Headless pipeline validation
└── requirements.txt
```

---

## Phase 2 roadmap (post-hackathon)

1. **TFLite CNN classifier** — replace threshold rules with a temporal CNN
   trained on labelled neonatal video datasets (PhysioNet MIMIC-III).

2. **ROI auto-detection** — use a face/body detector to automatically crop
   to the infant's chest and face region.

3. **SpO₂ proxy** — ratio of red/green channel amplitudes correlates with
   oxygen saturation (requires calibration against pulse oximeter ground truth).

4. **Flutter app** — wrap the Python pipeline via `flet` or rewrite core
   EVM in Dart/C++ for native mobile deployment.

5. **Clinician dashboard** — FastAPI backend + React frontend for remote
   monitoring of multiple patients.

---

## Scientific basis

- Wadhwa et al. (2013). *Eulerian Video Magnification for Revealing Subtle Changes in the World*. ACM SIGGRAPH.
- de Haan & Jeanne (2013). *Robust Pulse Rate From Chrominance-Based rPPG*. IEEE T-BME.
- Poh et al. (2011). *Non-contact, automated cardiac pulse measurements using video imaging and blind source separation*. Optics Express.
