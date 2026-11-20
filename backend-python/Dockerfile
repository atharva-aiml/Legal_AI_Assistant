# Production image for the whole backend (auth + CRUD + AI), one uvicorn process.
# Builds on both x86-64 and ARM64 (Oracle Cloud Ampere) — the PyTorch CPU index
# publishes wheels for both.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf \
    EASYOCR_MODULE_PATH=/models/easyocr

# libglib2.0-0: needed by opencv-python-headless (EasyOCR's image backend).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch first (CLAUDE.md §4 — the default PyPI wheel drags in CUDA),
# pinned to the versions the dev venv runs.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 torchvision==0.28.0

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake both models into the image so the first upload/chat doesn't download
# them at request time (and a container restart never re-downloads).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
 && python -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='/models/easyocr')"

COPY app ./app

ENV STORAGE_DIR=/data/uploads
VOLUME ["/data/uploads"]
EXPOSE 8080

# One worker on purpose: the hourly notification scheduler and the ingestion
# threads live in-process — several workers would each run their own scan.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
