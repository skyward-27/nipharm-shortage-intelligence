FROM python:3.11-slim

WORKDIR /app

# Install system deps (needed for some numpy/scipy builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Run from the server directory so relative model paths (./model/) resolve correctly
WORKDIR /app/server
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
