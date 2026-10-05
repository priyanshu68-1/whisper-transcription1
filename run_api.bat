@echo off
TITLE WhisperSense AI - FastAPI REST API Service
echo ==============================================================================
echo            WhisperSense AI • Production FastAPI REST Service
echo ==============================================================================
echo.
echo Starting FastAPI REST backend on http://127.0.0.1:8000...
echo Interactive Swagger Documentation: http://127.0.0.1:8000/docs
echo ReDoc Documentation: http://127.0.0.1:8000/redoc
echo Press Ctrl+C in this console to stop the API server.
echo.

python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start FastAPI backend.
    echo Make sure Python and requirements are installed: pip install -r requirements.txt
    pause
)
