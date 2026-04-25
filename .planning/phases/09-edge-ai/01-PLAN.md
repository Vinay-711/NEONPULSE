---
wave: 1
depends_on: [08-sms-alerts]
files_modified:
  - neopulse-backend/services/classifier.py
autonomous: true
---

# Phase 09: Edge AI Optimization (Plan 01)

## Objective
Convert the trained Random Forest classifier into ONNX format and replace the heavy Scikit-Learn inference mechanism with `onnxruntime` for edge hardware performance.

## Requirements
- **EDGE-01**: The Random Forest Apnea classification model is exported to ONNX or TensorFlow Lite to reduce memory footprint.
- **EDGE-02**: Fast inference engine replaces Scikit-Learn for prediction on limited hardware.

## Tasks

### 1. ONNX Model Export Utility
**Description:** Implement `skl2onnx` export logic so the model is converted efficiently after training.
<read_first>
- .planning/REQUIREMENTS.md
- neopulse-backend/services/classifier.py
</read_first>
<action>
Modify `neopulse-backend/services/classifier.py`:
- Add a new function `export_to_onnx()` that loads `neopulse_model.pkl`.
- Use `skl2onnx` (`convert_sklearn`) and `FloatTensorType` to convert the `RandomForestClassifier` into an ONNX representation.
- Save the ONNX model to disk as `neopulse_model.onnx`.
</action>
<acceptance_criteria>
- `neopulse-backend/services/classifier.py` contains `def export_to_onnx`
- `neopulse-backend/services/classifier.py` writes to `neopulse_model.onnx`
</acceptance_criteria>

### 2. ONNX Runtime Inference Integration
**Description:** Replace or provide an alternative to the Scikit-Learn `.predict()` method using `onnxruntime.InferenceSession`.
<read_first>
- neopulse-backend/services/classifier.py
</read_first>
<action>
Modify `neopulse-backend/services/classifier.py`:
- Implement a `predict_apnea_onnx(features)` function.
- Check if `neopulse_model.onnx` exists; if so, load it via `onnxruntime.InferenceSession`.
- Prepare the input tensor from the provided features and execute `sess.run()`.
- Return the predicted class.
</action>
<acceptance_criteria>
- `neopulse-backend/services/classifier.py` contains `def predict_apnea_onnx`
- `neopulse-backend/services/classifier.py` imports `onnxruntime`
</acceptance_criteria>

## Verification
- Verify the `export_to_onnx` and `predict_apnea_onnx` functions exist in the file and utilize the proper `onnx` and `onnxruntime` libraries.
