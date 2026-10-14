FROM python:3.11-slim
WORKDIR /app

# install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y build-essential libjpeg-dev zlib1g-dev && \
    pip install --no-cache-dir -r requirements.txt && rm -rf /var/lib/apt/lists/*

COPY backend/app /app/app
WORKDIR /app

ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
