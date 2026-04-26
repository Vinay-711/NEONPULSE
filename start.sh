#!/bin/bash
export PYTHONPATH="/tmp/neopulse_deps:$PYTHONPATH"
cd neopulse-backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
