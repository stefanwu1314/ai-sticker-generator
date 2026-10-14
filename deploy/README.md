# How to run (dev)

Prereqs: Docker & docker-compose, Node.js (for frontend dev)

1) Start backend stack (Redis + MinIO + API + worker)

  docker-compose up --build

This will start:
- API (http://localhost:8000)
- MinIO (http://localhost:9000) - access minioadmin/minioadmin
- Redis
- Celery worker

2) Run frontend in dev mode (in a separate terminal)

  cd frontend
  npm install
  npm run dev

Open http://localhost:5173 and try uploading a pet image and generating a sticker.

Notes:
- The backend currently uses a simple Pillow-based generator as a placeholder. To integrate real Chinese AI providers, implement call logic in backend/app/model_client.py (call_remote_provider or replace generate_sticker_from_image_bytes with remote provider responses).
- Environment variables for backend: MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET, MINIO_BUCKET, CELERY_BROKER_URL
- For production, replace SQLite with Postgres and run services on k8s or cloud.
