from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import video, signals, dataset, alerts

app = FastAPI(title="NeoPulse Backend API")

origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video.router)
app.include_router(signals.router)
app.include_router(dataset.router)
app.include_router(alerts.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0"}
