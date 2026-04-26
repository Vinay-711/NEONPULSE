import numpy as np
import matplotlib.pyplot as plt
import json

def generate_synthetic_dataset(n_samples=2500):
    np.random.seed(42)
    # Healthy Neonatal baselines
    true_hr = np.random.normal(140, 8, n_samples)
    true_rr = np.random.normal(45, 6, n_samples)
    
    # Tachypnea & Tachycardia (15%)
    idx_tachy = np.random.choice(n_samples, size=int(0.15 * n_samples), replace=False)
    true_hr[idx_tachy] = np.random.normal(185, 10, len(idx_tachy))
    true_rr[idx_tachy] = np.random.normal(70, 8, len(idx_tachy))
    
    # Apnea / Bradycardia (10%)
    remaining_idx = np.setdiff1d(np.arange(n_samples), idx_tachy)
    idx_brady = np.random.choice(remaining_idx, size=int(0.10 * n_samples), replace=False)
    true_hr[idx_brady] = np.random.normal(75, 5, len(idx_brady))
    true_rr[idx_brady] = np.random.normal(12, 4, len(idx_brady))
    
    # Simulated EVM Output (with baseline noise)
    evm_hr = true_hr + np.random.normal(0, 3.5, n_samples)
    evm_rr = true_rr + np.random.normal(0, 2.0, n_samples)
    
    # Motion artifacts
    idx_motion = np.random.choice(n_samples, size=int(0.08 * n_samples), replace=False)
    evm_hr[idx_motion] += np.random.normal(0, 18, len(idx_motion))
    evm_rr[idx_motion] += np.random.normal(0, 10, len(idx_motion))
    
    return true_hr, true_rr, evm_hr, evm_rr

def classify_alert_state(hr, rr):
    classes = np.zeros(len(hr), dtype=int)
    for i in range(len(hr)):
        if hr[i] < 80 or hr[i] > 180 or rr[i] < 20 or rr[i] > 80:
            classes[i] = 2 # EMERGENCY
        elif hr[i] < 100 or hr[i] > 160 or rr[i] < 30 or rr[i] > 60:
            classes[i] = 1 # CAUTION
        else:
            classes[i] = 0 # NORMAL
    return classes

def compute_bland_altman_stats(true_vals, est_vals):
    diff = est_vals - true_vals
    mean_bias = np.mean(diff)
    std_diff = np.std(diff)
    loa_upper = mean_bias + 1.96 * std_diff
    loa_lower = mean_bias - 1.96 * std_diff
    return mean_bias, loa_upper, loa_lower, diff

def plot_bland_altman(ax, true_vals, est_vals, title, color):
    mean_bias, loa_upper, loa_lower, diff = compute_bland_altman_stats(true_vals, est_vals)
    mean_vals = (true_vals + est_vals) / 2
    
    ax.scatter(mean_vals, diff, alpha=0.4, color=color, s=15, edgecolors='none')
    ax.axhline(mean_bias, color='k', linestyle='-', lw=2, label=f'Mean Bias: {mean_bias:.2f}')
    ax.axhline(loa_upper, color='#6b7280', linestyle='--', lw=2, label=f'+1.96 SD: {loa_upper:.2f}')
    ax.axhline(loa_lower, color='#6b7280', linestyle='--', lw=2, label=f'-1.96 SD: {loa_lower:.2f}')
    
    ax.set_title(title, fontweight='bold', pad=10)
    ax.set_xlabel('Mean of Ground Truth & EVM Estimate')
    ax.set_ylabel('Difference (EVM - Truth)')
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(True, linestyle=':', alpha=0.6)

def build_confusion_matrix(y_true, y_pred, num_classes=3):
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm

def compute_roc_auc(y_true, y_scores):
    thresholds = np.sort(np.unique(y_scores))[::-1]
    fpr, tpr = [0], [0]
    P = np.sum(y_true == 1)
    N = np.sum(y_true == 0)
    if P == 0 or N == 0:
        return [0,1], [0,1], 0.0
    for t in thresholds:
        fp = np.sum((y_scores >= t) & (y_true == 0))
        tp = np.sum((y_scores >= t) & (y_true == 1))
        fpr.append(fp / N)
        tpr.append(tp / P)
    fpr, tpr = np.array(fpr), np.array(tpr)
    auc_score = np.trapz(tpr, fpr)
    return fpr, tpr, auc_score

def run_evaluation():
    print("Generating NeoPulse evaluation dataset...")
    true_hr, true_rr, evm_hr, evm_rr = generate_synthetic_dataset(3000)
    
    print("Classifying clinical states...")
    true_classes = classify_alert_state(true_hr, true_rr)
    evm_classes = classify_alert_state(evm_hr, evm_rr)
    
    # 1. Continuous Regression Metrics
    hr_mae = np.mean(np.abs(true_hr - evm_hr))
    hr_rmse = np.sqrt(np.mean((true_hr - evm_hr)**2))
    rr_mae = np.mean(np.abs(true_rr - evm_rr))
    rr_rmse = np.sqrt(np.mean((true_rr - evm_rr)**2))
    
    hr_bias, hr_loa_u, hr_loa_l, _ = compute_bland_altman_stats(true_hr, evm_hr)
    rr_bias, rr_loa_u, rr_loa_l, _ = compute_bland_altman_stats(true_rr, evm_rr)
    
    # 2. Classification Metrics
    cm = build_confusion_matrix(true_classes, evm_classes, num_classes=3)
    class_names = ['NORMAL', 'CAUTION', 'EMERGENCY']
    class_metrics = {}
    
    for i, name in enumerate(class_names):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        tn = cm.sum() - (tp + fp + fn)
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        class_metrics[name] = {
            "sensitivity": float(round(sensitivity, 4)),
            "specificity": float(round(specificity, 4))
        }
        
    # 3. Export JSON
    summary = {
        "dataset_size": len(true_hr),
        "heart_rate_bpm": {
            "MAE": round(hr_mae, 3),
            "RMSE": round(hr_rmse, 3),
            "mean_bias": round(hr_bias, 3),
            "limits_of_agreement": [round(hr_loa_l, 3), round(hr_loa_u, 3)]
        },
        "respiratory_rate_bpm": {
            "MAE": round(rr_mae, 3),
            "RMSE": round(rr_rmse, 3),
            "mean_bias": round(rr_bias, 3),
            "limits_of_agreement": [round(rr_loa_l, 3), round(rr_loa_u, 3)]
        },
        "classification_performance": class_metrics
    }
    
    json_path = '/Users/vinxy/NEONPULSE/neopulse/evaluation_summary.json'
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=4)
        
    # 4. Render 4-Panel Report
    print("Rendering Matplotlib report...")
    plt.style.use('default')
    fig, axs = plt.subplots(2, 2, figsize=(16, 14))
    fig.patch.set_facecolor('#f9fafb')
    fig.suptitle('NeoPulse EVM Clinical Validation Report', fontsize=22, fontweight='bold', y=0.96)
    
    plot_bland_altman(axs[0, 0], true_hr, evm_hr, 'Bland-Altman: Heart Rate (BPM)', '#ef4444')
    plot_bland_altman(axs[0, 1], true_rr, evm_rr, 'Bland-Altman: Respiratory Rate (B/min)', '#3b82f6')
    
    hr_risk_factor = np.abs(evm_hr - 130) / 30 
    rr_risk_factor = np.abs(evm_rr - 45) / 25
    total_anomaly_risk = hr_risk_factor + rr_risk_factor
    
    y_true_binary = (true_classes == 2).astype(int)
    fpr, tpr, roc_auc = compute_roc_auc(y_true_binary, total_anomaly_risk)
    
    axs[1, 0].plot(fpr, tpr, color='#8b5cf6', lw=3, label=f'EVM Anomaly Risk (AUC = {roc_auc:.3f})')
    axs[1, 0].plot([0, 1], [0, 1], color='#9ca3af', lw=2, linestyle='--')
    axs[1, 0].set_xlim([0.0, 1.0])
    axs[1, 0].set_ylim([0.0, 1.05])
    axs[1, 0].set_xlabel('False Positive Rate', fontweight='bold')
    axs[1, 0].set_ylabel('True Positive Rate', fontweight='bold')
    axs[1, 0].set_title('ROC Curve: EMERGENCY vs REST', fontweight='bold', pad=10)
    axs[1, 0].legend(loc="lower right", framealpha=0.9)
    axs[1, 0].grid(True, linestyle=':', alpha=0.6)
    
    cax = axs[1, 1].matshow(cm, cmap='Blues', alpha=0.8)
    fig.colorbar(cax, ax=axs[1, 1], fraction=0.046, pad=0.04)
    
    for (i, j), z in np.ndenumerate(cm):
        color = 'white' if z > (np.max(cm) / 2) else 'black'
        axs[1, 1].text(j, i, f'{z}', ha='center', va='center', fontweight='bold', color=color)
        
    axs[1, 1].set_xticks(np.arange(len(class_names)))
    axs[1, 1].set_yticks(np.arange(len(class_names)))
    axs[1, 1].set_xticklabels(class_names, fontweight='bold')
    axs[1, 1].set_yticklabels(class_names, fontweight='bold')
    axs[1, 1].xaxis.set_ticks_position('bottom')
    axs[1, 1].set_xlabel('EVM Predicted Class', fontweight='bold')
    axs[1, 1].set_ylabel('Ground Truth Class', fontweight='bold')
    axs[1, 1].set_title('Rule-Based Classification Matrix', fontweight='bold', pad=10)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    
    png_path = '/Users/vinxy/NEONPULSE/neopulse/evaluation_report.png'
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    
    print(f"Success! \n- JSON Summary: {json_path}\n- Visual Report: {png_path}")

if __name__ == '__main__':
    run_evaluation()
