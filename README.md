# ai-sticker-generator

Starter repo: Vue3 frontend + FastAPI backend (gateway) that calls external Chinese AI APIs for sticker / meme generation. This starter implements an MVP where the backend delegates AI to external providers (configurable) — currently includes a mock generator using Pillow so you can run end-to-end locally.

Features included in this starter:
- Vue3 + Vite frontend with a simple Upload/Editor to create pet memes (upload image, add top/bottom text, pick template)
- FastAPI backend with async endpoints to upload images, create generation tasks, query task status
- Celery worker (Redis broker) that runs the generation job and writes result to MinIO
- MinIO object storage for storing uploaded images and generated stickers
- Docker Compose to run api, worker, redis, minio

See deploy/ and README for how to run.
