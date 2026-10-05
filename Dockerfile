# ==============================================================================
# WhisperSense AI • Production Multi-Stage Container Dockerfile
# Provides runtime environments for both Streamlit Dashboard (8501) and FastAPI (8000)
# ==============================================================================

FROM python:3.11-slim AS base

# System environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8501

# Install system dependencies including ffmpeg for audio processing and libsndfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and application assets
COPY . .

# Create directory for persistent data, uploads, and logs
RUN mkdir -p /app/data /app/exports

# Expose ports for Streamlit (8501) and FastAPI (8000)
EXPOSE 8501 8000

# Health check to ensure the service is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || curl -f http://localhost:8000/docs || exit 1

# Default command starts the Streamlit Dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
