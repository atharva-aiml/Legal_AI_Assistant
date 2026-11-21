# Production image for the whole backend (auth + CRUD + AI), one uvicorn process.
# Torch-free (CLAUDE.md §4): embeddings via fastembed, OCR via RapidOCR, both on
# ONNX Runtime — builds on x86-64 and ARM64 (Oracle Cloud Ampere A1).
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

# Bake both models into the image so a cold start never downloads them
# (CLAUDE.md §4: fastembed cache dir). Done directly against the libraries —
# importing app.infrastructure.config would demand GOOGLE_API_KEY at build time.
# RapidOCR stores its ONNX models inside its own package directory.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/models/fastembed')" \
 && python -c "from rapidocr import RapidOCR; RapidOCR()"

COPY app ./app

ENV STORAGE_DIR=/data/uploads
EXPOSE 8080

# One worker on purpose: the hourly notification scheduler and the ingestion
# threads live in-process — several workers would each run their own scan.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
