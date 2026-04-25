---
wave: 1
depends_on: [01-core-signal-pipeline]
files_modified:
  - neopulse-backend/services/evm.py
  - neopulse-backend/services/classifier.py
autonomous: true
---

# Phase 2: Rate Estimation & Heuristics (Plan 01)

## Objective
Convert raw signals into actionable BPM and breathing rates with clinical thresholds. Build the deterministic rule-based alert engine.

## Requirements
- Implement peak detection algorithms over the filtered signals.
- Calculate signal confidence scores based on interval standard deviations.
- Build the deterministic rule-based alert engine (Normal, Caution, Emergency).

## Tasks

### 1. Implement Rate Estimation
**Description:** Implement `estimate_heart_rate` and `estimate_breathing_rate` using `scipy.signal.find_peaks` to compute intervals and BPM. Implement confidence scoring logic based on standard deviations.
<read_first>
- .planning/ROADMAP.md
- neopulse-backend/services/evm.py
</read_first>
<action>
Modify `neopulse-backend/services/evm.py` to add:
- `estimate_heart_rate(signal, fs)`: peak prominence=0.1, distance=fs*0.4. Return (BPM, std).
- `estimate_breathing_rate(signal, fs)`: peak prominence=0.05, distance=fs*0.8. Return (BPM, std).
- `compute_confidence(std, type)`: Return a 0-100 float confidence metric.
</action>
<acceptance_criteria>
- `neopulse-backend/services/evm.py` contains `def estimate_heart_rate`
- `neopulse-backend/services/evm.py` contains `def estimate_breathing_rate`
- `neopulse-backend/services/evm.py` contains `def compute_confidence`
</acceptance_criteria>

### 2. Implement Rule-Based Classification
**Description:** Build the fallback clinical rule-engine that assigns 'NORMAL', 'CAUTION', or 'EMERGENCY' states based on fixed physiological thresholds.
<read_first>
- .planning/REQUIREMENTS.md
- neopulse-backend/services/classifier.py
</read_first>
<action>
Create or modify `neopulse-backend/services/classifier.py` to include a `classify_vitals_rules(hr, rr)` method.
- **EMERGENCY**: HR < 80 or > 180, RR < 20 or > 70.
- **CAUTION**: HR 80-100 or 160-180, RR 20-30 or 60-70.
- **NORMAL**: everything else.
</action>
<acceptance_criteria>
- `neopulse-backend/services/classifier.py` contains `classify_vitals_rules`
- `neopulse-backend/services/classifier.py` contains thresholds `80`, `180`, `20`, `70`
</acceptance_criteria>

## Verification
- Verify functions exist via grep.
