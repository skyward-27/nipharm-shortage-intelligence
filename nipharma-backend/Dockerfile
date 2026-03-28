FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Run from the server directory so relative imports work correctly
WORKDIR /app/server
CMD uvicorn main:app --host 0.0.0.0 --port 8080
