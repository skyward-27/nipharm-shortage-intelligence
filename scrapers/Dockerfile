# NiPharm Scrapers — Docker environment
# Pins exact versions that make SHAP + XGBoost + numpy work together.
#
# BUILD:  docker build -t nipharma-scrapers .
# TRAIN:  docker run --rm \
#           -v "$(pwd)/data:/scrapers/data" \
#           -v "$(pwd)/../nipharma-backend/model:/backend/model" \
#           nipharma-scrapers python 12_ml_model_panel.py
# ANY SCRIPT: docker run --rm -v "$(pwd)/data:/scrapers/data" nipharma-scrapers python 04_mhra_alerts.py

FROM python:3.11-slim

WORKDIR /scrapers

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl git \
    && rm -rf /var/lib/apt/lists/*

# ── Core scientific stack — pinned for SHAP + XGBoost compatibility ───────────
# numpy <2.0 required by shap; numba 0.57+ fixes _internal init failure
RUN pip install --no-cache-dir \
    "numpy>=1.24,<2.0" \
    "pandas>=2.0,<3.0" \
    "scikit-learn>=1.3,<2.0" \
    "xgboost>=1.7,<3.0" \
    "numba>=0.57,<0.60" \
    "llvmlite>=0.40,<0.43" \
    "shap>=0.43,<0.46"

# ── Data scraping ─────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    lxml \
    openpyxl \
    python-dotenv \
    playwright \
    yfinance \
    pdfplumber \
    tqdm

# Install Playwright browsers (needed for MHRA / BSO scrapers)
RUN playwright install chromium --with-deps || true

# ── Copy scraper scripts ───────────────────────────────────────────────────────
COPY *.py ./

# Default command — training (override with docker run ... python XX_script.py)
CMD ["python", "12_ml_model_panel.py"]
