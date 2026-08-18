# Multi-Stage Dockerfile for MedData AI (Streamlit + FastAPI)
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source code
COPY . .

# Initialize and seed the SQLite database
RUN python -c "from database import init_database; init_database(force_reset=True)"

# Expose ports: 8501 (Streamlit Frontend) and 8000 (FastAPI Backend)
EXPOSE 8501 8000

# Default entrypoint: Run Streamlit UI
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
