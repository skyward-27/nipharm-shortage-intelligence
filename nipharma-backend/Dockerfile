FROM python:3.11-slim

# Install system deps for numpy/pandas/xgboost/duckdb C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + model files
COPY . .

# Verify critical files are present
RUN ls -lh /app/model/ || echo "WARNING: model/ directory missing"
RUN ls -lh /app/server/ || echo "WARNING: server/ directory missing"
RUN python -c "import duckdb; print('duckdb OK:', duckdb.__version__)" || echo "WARNING: duckdb import failed"

# Run from /app/server so 'from explorer import run_query' resolves correctly
# CWD=/app/server → sys.path includes /app/server → explorer.py found
WORKDIR /app/server

# Health check — Railway uses this to know when the app is ready
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/ping || exit 1

EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 30
