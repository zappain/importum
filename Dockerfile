
# UM MVP importer + API + primitive UI
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt fastapi==0.111.0 uvicorn==0.30.1

COPY src /app/src
COPY web /app/web
COPY config /app/config

# Default command: run API (expects um.db to exist; run importer first if needed)
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
