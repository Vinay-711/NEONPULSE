import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
from scipy.signal import find_peaks

try:
    import onnxruntime as rt
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

from config import DATA_DIR, HR_NORMAL, RR_NORMAL
from services.dataset_loader import list_records, load_record, get_apnea_labels

MODEL_PATH = os.path.join(DATA_DIR, 'neopulse_model.pkl')
ONNX_MODEL_PATH = os.path.join(DATA_DIR, 'neopulse_model.onnx')

def build_training_dataset():
    records = list_records('apnea-ecg')
    X_list = []
    y_list = []
    
    for rec_name in records:
        try:
            record_data = load_record('apnea-ecg', rec_name)
            labels = get_apnea_labels(rec_name)
        except Exception as e:
            continue
            
        fs = record_data['sample_rate']
        sig = record_data['signal']
        
        if sig.ndim > 1:
            sig = sig[:, 0]
            
        for label in labels:
            start_sec = label['start_sec']
            end_sec = label['end_sec']
            is_apnea = label['is_apnea']
            
            start_idx = int(start_sec * fs)
            end_idx = int(end_sec * fs)
            
            if end_idx > len(sig):
                continue
                
            segment = sig[start_idx:end_idx]
            
            # Simple peak detection for ECG
            if np.std(segment) > 0:
                norm_sig = (segment - np.mean(segment)) / np.std(segment)
            else:
                norm_sig = segment
                
            peaks, _ = find_peaks(norm_sig, distance=fs*0.4, prominence=0.5)
            
            if len(peaks) < 2:
                continue
                
            intervals = np.diff(peaks) / fs
            mean_hr = 60.0 / np.mean(intervals)
            std_hr = np.std(60.0 / intervals) if len(intervals) > 1 else 0.0
            mean_rr_interval = np.mean(intervals)
            
            X_list.append([mean_hr, std_hr, mean_rr_interval])
            y_list.append(1 if is_apnea else 0)
            
    return np.array(X_list), np.array(y_list)

def train_classifier(X, y):
    if len(X) == 0:
        print("No data to train on.")
        return
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    
    print("ROC AUC Score:")
    print(roc_auc_score(y_test, y_prob))
    
    os.makedirs(DATA_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

def load_classifier():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

def export_to_onnx():
    if not HAS_ONNX:
        print("ONNX libraries not installed. Skipping export.")
        return
    clf = load_classifier()
    if clf is None:
        print("No trained model found.")
        return
    initial_type = [('float_input', FloatTensorType([None, 3]))]
    onx = convert_sklearn(clf, initial_types=initial_type)
    with open(ONNX_MODEL_PATH, "wb") as f:
        f.write(onx.SerializeToString())
    print(f"ONNX model saved to {ONNX_MODEL_PATH}")

def predict_apnea_onnx(features):
    if not HAS_ONNX:
        return None, None
    if not os.path.exists(ONNX_MODEL_PATH):
        return None, None
    sess = rt.InferenceSession(ONNX_MODEL_PATH, providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    prob_name = sess.get_outputs()[1].name
    
    pred_onx = sess.run([label_name, prob_name], {input_name: features.astype(np.float32)})
    is_apnea = pred_onx[0][0] == 1
    # pred_onx[1] is typically a list of dicts mapping class to probability
    prob = pred_onx[1][0][1] # Probability of class 1
    return is_apnea, prob

def classify_vitals(hr_bpm: float, rr_bpm: float, hr_std: float, confidence: float) -> dict:
    clf = load_classifier()
    
    # Rule-based thresholds
    def classify_vitals_rules(hr, rr):
        state = "NORMAL"
        if hr < 80 or hr > 180 or rr < 20 or rr > 70:
            state = "EMERGENCY"
        elif (hr >= 80 and hr < HR_NORMAL[0]) or (hr > HR_NORMAL[1] and hr <= 180) or \
             (rr >= 20 and rr < RR_NORMAL[0]) or (rr > RR_NORMAL[1] and rr <= 70):
            state = "CAUTION"
        return {
            "state": state,
            "confidence": confidence,
            "method": "rules"
        }
    
    if clf is not None and hr_bpm > 0:
        mean_rr_interval = 60.0 / hr_bpm
        features = np.array([[hr_bpm, hr_std, mean_rr_interval]])
        
        try:
            # Phase 9: Attempt fast ONNX inference first
            is_apnea, prob = predict_apnea_onnx(features)
            if is_apnea is None:
                # Fallback to Scikit-Learn inference
                prob = clf.predict_proba(features)[0][1]
                is_apnea = clf.predict(features)[0] == 1
            
            # ML Model thresholding
            if is_apnea and prob >= 0.6:
                return {
                    "state": "EMERGENCY",
                    "confidence": prob * 100.0,
                    "method": "ml"
                }
            elif prob > 0.4:
                return {
                    "state": "CAUTION",
                    "confidence": prob * 100.0,
                    "method": "ml"
                }
            else:
                # ML predicts normal. Fallback to basic physiological bounds just in case.
                rules_res = classify_vitals_rules(hr_bpm, rr_bpm)
                if rules_res["state"] != "NORMAL":
                    return rules_res
                    
                return {
                    "state": "NORMAL",
                    "confidence": (1.0 - prob) * 100.0,
                    "method": "ml"
                }
        except Exception:
            return classify_vitals_rules(hr_bpm, rr_bpm)
            
    return classify_vitals_rules(hr_bpm, rr_bpm)
