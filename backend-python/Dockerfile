# Production image for the whole backend (auth + CRUD + AI), one uvicorn
# process — built and run by Google Cloud Run (`gcloud run deploy --source`).
# Torch-free (CLAUDE.md §4): embeddings via fastembed, OCR via RapidOCR.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_CACHE_DIR=/models/fastembed

# libglib2.0-0: needed by opencv-python-headless (RapidOCR's image backend).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake both models into the image so a cold start never downloads them.
# Called directly on the libraries — importing app.infrastructure.config would
# demand GOOGLE_API_KEY at build time. RapidOCR keeps its ONNX models inside
# its own package directory.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/models/fastembed')" \
 && python -c "from rapidocr import RapidOCR; RapidOCR()"

COPY app ./app

# Cloud Run mounts the Cloud Storage bucket here (see deploy command).
ENV STORAGE_DIR=/data/uploads

# One worker on purpose: the hourly notification scheduler and the ingestion
# threads live in-process. Cloud Run injects PORT (8080 by default).
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips "*"
