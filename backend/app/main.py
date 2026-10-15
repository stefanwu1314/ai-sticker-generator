import os
import re
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, get_session
from .db import Task
from .storage import upload_bytes, internal_presigned_url, ensure_bucket
from .celery_tasks import generate_sticker

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    ensure_bucket()
    yield


app = FastAPI(title='AI Sticker Generator Gateway', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _safe_filename(name: str | None, default: str = 'image.png') -> str:
    if not name:
        return default
    base = os.path.basename(name.replace('\\', '/'))
    base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    return base or default


@app.post('/api/v1/upload')
async def upload_image(file: UploadFile = File(...)):
    if file.content_type and not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='only image files are allowed')
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail='empty file')
    object_name = f"uploads/{uuid.uuid4().hex}-{_safe_filename(file.filename)}"
    url = upload_bytes(contents, object_name)
    return {
        'url': url,
        'internal_url': internal_presigned_url(object_name),
        'object_name': object_name,
    }


@app.post('/api/v1/tasks')
async def create_task(payload: dict):
    image_url = payload.get('image_url')
    if not image_url:
        raise HTTPException(status_code=400, detail='image_url required')
    reference_image_url = payload.get('reference_image_url')
    top_text = payload.get('top_text')
    bottom_text = payload.get('bottom_text')

    task_id = uuid.uuid4().hex
    t = Task(
        id=task_id,
        status='pending',
        input_image_url=image_url,
        reference_image_url=reference_image_url,
        top_text=top_text,
        bottom_text=bottom_text,
    )
    with get_session() as s:
        s.add(t)
        s.commit()

    generate_sticker.delay(task_id, image_url, reference_image_url, top_text, bottom_text)
    return {'task_id': task_id}


@app.get('/api/v1/tasks/{task_id}')
def get_task(task_id: str):
    with get_session() as s:
        t = s.get(Task, task_id)
        if not t:
            raise HTTPException(status_code=404, detail='task not found')
        return {'task_id': t.id, 'status': t.status, 'result_url': t.result_url, 'error': t.error}
