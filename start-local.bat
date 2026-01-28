@echo off
setlocal enabledelayedexpansion

echo [1/2] Starting AI Service...
start "AI-Service" cmd /k "cd robot-control-system\ai-service && if not exist venv (python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt) else (.\venv\Scripts\activate) && python main.py"

echo [2/2] Starting Frontend...
start "Frontend" cmd /k "cd robot-control-system\frontend && if not exist node_modules (npm install) && npm run dev"

echo All services are starting in separate windows.
echo Frontend will be available at http://localhost:5173
echo AI Service will be available at http://localhost:5000
pause
