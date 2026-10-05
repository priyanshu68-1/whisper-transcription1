@echo off
TITLE WhisperSense AI - Master Service Launcher
echo ==============================================================================
echo            WhisperSense AI • Master Service Orchestrator
echo ==============================================================================
echo.
echo Launching WhisperSense AI full platform stack:
echo   1. FastAPI REST API Service  -> http://127.0.0.1:8000
echo   2. Streamlit Web Dashboard   -> http://localhost:8501
echo.
echo Spawning API backend in a dedicated process window...
start "WhisperSense AI - FastAPI Backend (Port 8000)" cmd /k "run_api.bat"

echo Waiting 3 seconds for API service initialization...
timeout /t 3 /nobreak >nul

echo Spawning Streamlit frontend in a dedicated process window...
start "WhisperSense AI - Streamlit Dashboard (Port 8501)" cmd /k "run_dashboard.bat"

echo.
echo ==============================================================================
echo WhisperSense AI services are active!
echo Opening browser to http://localhost:8501...
echo ==============================================================================
timeout /t 2 /nobreak >nul
start http://localhost:8501
