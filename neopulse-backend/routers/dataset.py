from fastapi import APIRouter, BackgroundTasks, HTTPException
from services.dataset_loader import (
    download_apnea_ecg, 
    download_ninfea, 
    list_records, 
    load_record
)
from services.evm import estimate_heart_rate
from config import DATA_DIR
import numpy as np
import os
import json
from scipy.signal import find_peaks
from scipy.stats import pearsonr

router = APIRouter(prefix="/dataset", tags=["Dataset"])

@router.get("/download/{db_name}")
def trigger_download(db_name: str, background_tasks: BackgroundTasks):
    if db_name == 'apnea-ecg':
        background_tasks.add_task(download_apnea_ecg)
        return {"message": f"Downloading {db_name} in background..."}
    elif db_name == 'ninfea':
        background_tasks.add_task(download_ninfea)
        return {"message": f"Downloading {db_name} in background..."}
    else:
        raise HTTPException(status_code=400, detail="Unknown database name. Try 'apnea-ecg' or 'ninfea'.")

@router.get("/records/{db_name}")
def get_records(db_name: str):
    records = list_records(db_name)
    if not records:
        raise HTTPException(status_code=404, detail=f"No records found for {db_name}. Might need to download first.")
    return {"db_name": db_name, "records": records}

@router.get("/record/{db_name}/{record_name}")
def get_record_data(db_name: str, record_name: str):
    try:
        record_data = load_record(db_name, record_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    fs = record_data["sample_rate"]
    sig = record_data["signal"]
    
    # Get first 10 seconds of data
    num_samples = min(int(10 * fs), len(sig))
    
    # Grab the first channel for simplicity
    channel_0_data = sig[:num_samples, 0] if sig.ndim > 1 else sig[:num_samples]
    
    # Replace NaNs with 0.0 for JSON serialization
    channel_0_data = np.nan_to_num(channel_0_data, nan=0.0).tolist()
    
    # Filter non-serializable dict fields
    serializable_fields = {}
    for k, v in record_data["fields"].items():
        if isinstance(v, (str, int, float, bool, list, dict)):
            serializable_fields[k] = v
    
    return {
        "db_name": db_name,
        "record_name": record_name,
        "sample_rate": fs,
        "duration_sec": record_data["duration_sec"],
        "fields": serializable_fields,
        "signal_10s": channel_0_data
    }

@router.post("/validate-evm")
def validate_evm():
    records = list_records('ninfea')
    if not records:
        raise HTTPException(status_code=404, detail="NInFEA dataset not found. Download it first.")
        
    # Take first 5 records
    records_to_test = records[:5]
    
    results = []
    true_hrs = []
    est_hrs = []
    
    for rec_name in records_to_test:
        try:
            record_data = load_record('ninfea', rec_name)
        except Exception:
            continue
            
        fs = record_data["sample_rate"]
        sig = record_data["signal"]
        
        # Grab first channel (typically ECG)
        if sig.ndim > 1:
            ecg = sig[:, 0]
        else:
            ecg = sig
            
        # Clean NaNs
        ecg = np.nan_to_num(ecg, nan=0.0)
        
        # Ground truth HR from ECG
        if np.std(ecg) > 0:
            norm_ecg = (ecg - np.mean(ecg)) / np.std(ecg)
        else:
            norm_ecg = ecg
            
        peaks, _ = find_peaks(norm_ecg, prominence=0.5, distance=fs*0.3)
        if len(peaks) < 2:
            continue
            
        intervals = np.diff(peaks) / fs
        true_hr = 60.0 / np.mean(intervals) if np.mean(intervals) > 0 else 0.0
        
        # Simulated rPPG
        noise = np.random.normal(0, 0.1, size=len(ecg))
        simulated_rppg = norm_ecg + noise
        
        est_hr, conf = estimate_heart_rate(simulated_rppg, fs)
        
        error = abs(true_hr - est_hr)
        
        results.append({
            "record_name": rec_name,
            "true_hr": float(true_hr),
            "estimated_hr": float(est_hr),
            "error_bpm": float(error),
            "confidence": float(conf)
        })
        
        true_hrs.append(true_hr)
        est_hrs.append(est_hr)
        
    if not results:
        raise HTTPException(status_code=400, detail="Could not process any records.")
        
    # Metrics
    mae = np.mean([r["error_bpm"] for r in results])
    rmse = np.sqrt(np.mean([r["error_bpm"]**2 for r in results]))
    pearson_r, _ = pearsonr(true_hrs, est_hrs) if len(true_hrs) > 1 else (0.0, 0.0)
    mean_conf = np.mean([r["confidence"] for r in results])
    
    report = {
        "records_tested": len(results),
        "mae_bpm": float(mae),
        "rmse_bpm": float(rmse),
        "pearson_r": float(pearson_r),
        "mean_confidence": float(mean_conf),
        "per_record": results
    }
    
    # Save to file
    benchmark_path = os.path.join(DATA_DIR, 'benchmark.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(benchmark_path, 'w') as f:
        json.dump(report, f, indent=2)
        
    return report

@router.get("/benchmark-report")
def get_benchmark_report():
    benchmark_path = os.path.join(DATA_DIR, 'benchmark.json')
    if not os.path.exists(benchmark_path):
        raise HTTPException(status_code=404, detail="No benchmark report found. Run /validate-evm first.")
        
    with open(benchmark_path, 'r') as f:
        return json.load(f)
