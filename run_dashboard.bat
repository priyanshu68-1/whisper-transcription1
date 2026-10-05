@echo off
TITLE WhisperSense AI - Streamlit Web Dashboard
echo ==============================================================================
echo            WhisperSense AI • Meeting Intelligence Dashboard
echo ==============================================================================
echo.
echo Starting Streamlit web application on http://localhost:8501...
echo Press Ctrl+C in this console to stop the dashboard server.
echo.

python -m streamlit run app.py --server.port 8501
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start Streamlit dashboard.
    echo Make sure Python and requirements are installed: pip install -r requirements.txt
    pause
)
