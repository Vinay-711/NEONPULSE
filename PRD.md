🧠 NeoPulse AI

Non-contact neonatal monitoring using smartphone camera + AI

⸻

📄 1. PRD (Product Requirements Document)

🧩 Product Overview

NeoPulse AI is a non-contact neonatal monitoring system that uses a smartphone camera and AI to detect early signs of abnormal breathing and heart rate in newborns.

⸻

🎯 Objectives
	•	Enable early detection of neonatal risks at home
	•	Provide affordable monitoring without hardware
	•	Assist parents with real-time alerts

⸻

👤 Target Users
	•	New parents (especially rural/underserved)
	•	Healthcare workers (ASHA, nurses)
	•	Pediatricians (for remote monitoring)

⸻

🚨 Problem Statement

Newborns are discharged early, but life-threatening conditions often develop within the first week. Parents lack tools to monitor vital signs.

⸻

💡 Solution

A smartphone-based system that:
	•	Captures video of infant
	•	Extracts vital signals using computer vision
	•	Uses AI to detect abnormalities
	•	Sends alerts to caregivers

⸻

⚙️ Core Features

MVP Features
	•	Camera-based monitoring
	•	Breathing rate detection
	•	Basic alert system

Advanced Features
	•	Heart rate estimation
	•	AI-based anomaly detection
	•	Doctor dashboard
	•	Offline (Edge AI)

⸻

🧠 Functional Requirements
	•	Capture real-time video input
	•	Detect chest motion and extract breathing signal
	•	Analyze signal for abnormalities
	•	Trigger alerts when thresholds exceeded
	•	Store session data (optional)

⸻

🔒 Non-Functional Requirements
	•	Low latency (real-time processing)
	•	Works in low connectivity (offline support)
	•	Data privacy and encryption
	•	High sensitivity detection

⸻

⚠️ Constraints
	•	Lighting variability
	•	Baby movement noise
	•	Limited medical dataset

⸻

📊 Success Metrics
	•	Detection accuracy
	•	False negative rate (critical)
	•	User adoption

⸻

📦 2. requirements.txt

opencv-python
numpy
scipy
matplotlib
tensorflow
tflite-runtime
scikit-learn
imutils
fastapi
uvicorn
pydantic
python-multipart

⸻

📖 3. README.md

🚀 NeoPulse AI

NeoPulse AI is a non-contact neonatal monitoring system that uses a smartphone camera and AI to detect early signs of abnormal breathing and heart rate in newborns.

⸻

🎯 Problem

Newborns are often discharged within 24–48 hours, but critical conditions like respiratory distress occur within the first week. Parents lack tools to monitor vital signs at home.

⸻

💡 Solution

NeoPulse AI uses:
	•	Smartphone camera
	•	Eulerian Video Magnification (EVM)
	•	AI-based pattern analysis

To extract:
	•	Breathing rate
	•	Heart rate (experimental)

⸻

⚙️ Features
	•	📹 Non-contact monitoring
	•	🫁 Breathing rate detection
	•	❤️ Heart rate estimation
	•	🚨 Risk alerts
	•	📊 Simple dashboard

⸻

🏗️ Tech Stack
	•	Frontend: Flutter / React Native
	•	Backend: FastAPI
	•	AI/ML: TensorFlow, OpenCV
	•	Edge: TensorFlow Lite

⸻

🧪 How It Works
	1.	Capture video of infant
	2.	Extract subtle signals using EVM
	3.	Convert to time-series data
	4.	Analyze with AI model
	5.	Trigger alerts if abnormal

⸻

▶️ Getting Started

1. Clone repo

git clone https://github.com/your-username/neopulse-ai.git
cd neopulse-ai

2. Install dependencies

pip install -r requirements.txt

3. Run backend

uvicorn main:app --reload


⸻

📊 Future Improvements
	•	Clinical validation
	•	Improved accuracy
	•	Doctor dashboard
	•	Offline edge optimization

⸻

⚠️ Disclaimer

This system is not a medical diagnostic device. It is an assistive tool for early risk detection only.

⸻

🤝 Contributing

Pull requests are welcome.

⸻

📜 License

MIT License