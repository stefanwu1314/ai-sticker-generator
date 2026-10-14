from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
from .database import init_db, get_session
from .db import Task
from .storage import upload_bytes
from .celery_tasks import generate_sticker

app = FastAPI(title='AI Sticker Generator Gateway')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event('startup')
def on_startup():
    init_db()

@app.post('/api/v1/upload')
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    object_name = f"uploads/{uuid.uuid4().hex}-{file.filename}"
    url = upload_bytes(contents, object_name)
    return {'url': url}

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
