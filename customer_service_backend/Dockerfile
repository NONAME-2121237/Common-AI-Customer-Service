FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config.yaml .
COPY run.py .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV USE_SIMPLE_MEMORY=${USE_SIMPLE_MEMORY:-true}

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
