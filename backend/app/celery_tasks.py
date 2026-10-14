from celery import Celery
import os
from .database import get_session, init_db
from .db import Task
from .storage import upload_bytes
import httpx
from .model_client import generate_sticker_from_image_bytes

CELERY_BROKER = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
celery_app = Celery('worker', broker=CELERY_BROKER)

@celery_app.task(name='tasks.generate_sticker')
def generate_sticker(task_id: str, image_url: str, top_text: str | None, bottom_text: str | None):
    # Download image
    try:
        import requests
        r = requests.get(image_url, timeout=30)
        r.raise_for_status()
        image_bytes = r.content
        # call generator (mock Pillow overlay for starter)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out_bytes = loop.run_until_complete(generate_sticker_from_image_bytes(image_bytes, top_text, bottom_text))
        object_name = f"{task_id}.png"
        url = upload_bytes(out_bytes, object_name)
        # update DB
        with get_session() as s:
            t = s.get(Task, task_id)
            t.status = 'success'
            t.result_url = url
            s.add(t); s.commit()
    except Exception as e:
        with get_session() as s:
            t = s.get(Task, task_id)
            t.status = 'failed'
            t.error = str(e)
            s.add(t); s.commit()
