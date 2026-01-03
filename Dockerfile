FROM python:3.10-slim

# Install system dependencies
# ffmpeg: for audio processing
# git: for pip installing from git if needed
# libsndfile1: for soundfile/torchaudio
# libcairo2, libpango*: for CairoSVG
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libsndfile1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENTRYPOINT ["python", "-m", "src.main"]
