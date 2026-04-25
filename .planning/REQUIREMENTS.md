# Requirements

## 1. Core Workflows
- Parent opens app and points camera at newborn
- System tracks face/chest ROI and extracts vitals (HR/RR)
- System raises immediate alert if vitals fall outside normal physiological bounds

## 2. Table Stakes (Must-Haves)
- **Real-time Video Capture:** Performant camera loop
- **EVM Pipeline:** Motion and color magnification for signal extraction
- **Rule-based Alerts:** Thresholds for bradycardia, tachycardia, tachypnea, and apnea
- **Offline Capability:** Edge inference

## 3. Differentiators
- **AI Classification:** Random Forest classifier for advanced anomaly detection beyond static rules
- **Zero-Hardware:** Fully software-defined monitoring

## 4. Anti-Features (Out of Scope)
- Custom hardware integrations (wearables, pulse oximeters)
- Cloud-dependent critical alerting (alerts must fire offline)

## 5. Technical Constraints
- Real-time processing requires strict latency control (target 30fps)
- Must handle varying lighting conditions and slight movement
