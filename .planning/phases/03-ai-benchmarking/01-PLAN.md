---
wave: 1
depends_on: [02-rate-estimation]
files_modified:
  - neopulse-backend/services/classifier.py
  - neopulse-backend/routers/dataset.py
autonomous: true
---

# Phase 3: AI Integration & Benchmarking (Plan 01)

## Objective
Train and integrate the machine learning classifier using PhysioNet datasets and validate system accuracy against ground truth ECG.

## Requirements
- Extract features (mean HR, std HR, RR interval) from Apnea-ECG/NInFEA datasets.
- Train and deploy the Random Forest classifier.
- Validate system accuracy (MAE, RMSE, Pearson R) against ground truth ECG.

## Tasks

### 1. Build and Train Classifier
**Description:** Implement the scikit-learn Random Forest classifier pipeline on the Apnea-ECG dataset.
<read_first>
- .planning/ROADMAP.md
- neopulse-backend/services/classifier.py
</read_first>
<action>
Modify `neopulse-backend/services/classifier.py`:
- Implement `build_training_dataset()` to extract mean HR, std HR, and mean RR interval from `apnea-ecg` records.
- Implement `train_classifier(X, y)` using `RandomForestClassifier` with class weight balancing. Dump model to `neopulse_model.pkl`.
- Ensure `classify_vitals` routes through the ML model first before falling back to rules.
</action>
<acceptance_criteria>
- `neopulse-backend/services/classifier.py` contains `def build_training_dataset`
- `neopulse-backend/services/classifier.py` contains `def train_classifier`
- `neopulse-backend/services/classifier.py` contains `RandomForestClassifier`
</acceptance_criteria>

### 2. Implement EVM Benchmark Endpoint
**Description:** Add an endpoint to benchmark the EVM pipeline against NInFEA ground-truth ECG data.
<read_first>
- .planning/REQUIREMENTS.md
- neopulse-backend/routers/dataset.py
</read_first>
<action>
Modify `neopulse-backend/routers/dataset.py` to expose `POST /dataset/validate-evm`.
- Compute true HR using `scipy.signal.find_peaks` on the ECG channel.
- Add Gaussian noise to the ECG to simulate the rPPG signal.
- Run `evm.estimate_heart_rate()` on the noisy signal.
- Calculate MAE, RMSE, and Pearson R and return a JSON report.
</action>
<acceptance_criteria>
- `neopulse-backend/routers/dataset.py` contains `POST` endpoint for `/validate-evm`
- `neopulse-backend/routers/dataset.py` calculates `mae_bpm` and `rmse_bpm`
</acceptance_criteria>

## Verification
- Verify functions and endpoints exist via grep.
