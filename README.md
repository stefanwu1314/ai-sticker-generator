# ai-sticker-generator

Starter repo for a pet meme / sticker generator. Users upload pet photos and turn them into sticker-style animal meme images using a remote AI provider (Volcengine Ark / ByteDance, with a local mock fallback).

## Stack
- Vue 3 frontend
- FastAPI backend
- Celery + Redis worker
- MinIO object storage
- Docker Compose starter

## Local dev (demo / mock)

1. Copy `.env.example` to `.env` and adjust values (set `MODEL_PROVIDER=mock` to run without any AI provider key):

```bash
cp .env.example .env
```

2. Start infra + backend

```bash
docker-compose up --build
```

This starts Redis, MinIO (http://localhost:9000, console at http://localhost:9001), the FastAPI API (http://localhost:8000) and the Celery worker.

3. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, upload a pet photo, optionally a reference meme image, add texts and click Generate Sticker.

## Real AI provider config (Volcengine Ark / ByteDance)

In `.env`:

```bash
MODEL_PROVIDER=volcano
VOLCANO_API_URL=https://ark.cn-beijing.volces.com
VOLCANO_API_KEY=your_key_here
VOLCANO_MODEL=doubao-seedream-4-0-250828
```

Notes:
- `VOLCANO_MODEL` must be a valid image-generation model ID (`doubao-seedream-*`) or your Ark endpoint ID (`ep-xxx`). Do not use chat model IDs such as `doubao-seed-1-6`.
- Keep your API key in `.env` or secrets only — never commit it. If a key was ever leaked, rotate it in the Ark console.
- When the Ark call fails, the worker falls back to the local mock generator so the task flow still completes.

## How it works

1. Frontend uploads the pet photo (and optional reference meme) via `POST /api/v1/upload`; the API stores the object in MinIO and returns two presigned URLs — an external one for the browser and an internal one for the worker.
2. Frontend creates a task via `POST /api/v1/tasks` (passing the internal URLs); the API persists it in the shared SQLite database (`/app/data/data.db`) and dispatches a Celery job.
3. The worker downloads the images, calls the provider (Ark image generation with `data:image/png;base64,...` input images, or the Pillow mock), uploads the result to MinIO and stores an external presigned result URL.
4. Frontend polls `GET /api/v1/tasks/{task_id}` until status is `success` or `failed`, then shows/downloads the result.

## Project structure

```
backend/
  app/
    main.py           # FastAPI entry (upload / tasks endpoints)
    celery_tasks.py   # Celery worker task
    model_client.py   # provider abstraction (volcano + mock)
    storage.py        # MinIO helpers (internal + external presigned URLs)
    database.py       # SQLModel engine (DATABASE_URL)
    db.py             # Task model
  Dockerfile
  requirements.txt
frontend/
  src/
    components/UploadEditor.vue
    App.vue
    main.js
    style.css
deploy/
  README.md
docker-compose.yml
.env.example
```

## Important notes
- The SQLite database lives on the shared `app-data` docker volume, so the API and the worker see the same data. For production, switch `DATABASE_URL` to Postgres/MySQL.
- Add content safety checks before publishing user-generated images.
- Ensure provider keys are kept in environment variables or secrets, not committed to source control.
