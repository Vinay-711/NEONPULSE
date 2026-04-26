import os
import wfdb
import glob
from config import DATA_DIR

def download_apnea_ecg():
    target_dir = os.path.join(DATA_DIR, 'apnea-ecg')
    os.makedirs(target_dir, exist_ok=True)
    wfdb.dl_database('apnea-ecg', target_dir)

def download_ninfea():
    target_dir = os.path.join(DATA_DIR, 'ninfea')
    os.makedirs(target_dir, exist_ok=True)
    wfdb.dl_database('ninfea', target_dir)

def load_record(db_name: str, record_name: str):
    record_path = os.path.join(DATA_DIR, db_name, record_name)
    record = wfdb.rdrecord(record_path)
    
    return {
        "signal": record.p_signal,
        "fields": record.__dict__,
        "sample_rate": record.fs,
        "duration_sec": record.sig_len / record.fs if record.fs else 0.0
    }

def get_apnea_labels(record_name: str):
    record_path = os.path.join(DATA_DIR, 'apnea-ecg', record_name)
    
    try:
        ann = wfdb.rdann(record_path, 'apn')
    except FileNotFoundError:
        return []
    
    labels = []
    
    for idx, sample in enumerate(ann.sample):
        symbol = ann.symbol[idx]
        start_sec = sample / ann.fs if hasattr(ann, 'fs') and ann.fs else sample / 100.0
        labels.append({
            "start_sec": start_sec,
            "end_sec": start_sec + 60.0,
            "is_apnea": symbol == 'A'
        })
        
    return labels

def list_records(db_name: str):
    db_dir = os.path.join(DATA_DIR, db_name)
    if not os.path.exists(db_dir):
        return []
    
    hea_files = glob.glob(os.path.join(db_dir, '*.hea'))
    records = [os.path.splitext(os.path.basename(f))[0] for f in hea_files]
    return sorted(list(set(records)))
