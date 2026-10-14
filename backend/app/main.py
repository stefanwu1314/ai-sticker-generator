from celery import Celery
import os
import requests
from .database import get_session
from .db import Task
from .storage import upload_bytes
from .model_client import generate_sticker_from_image_bytes

CELERY_BROKER = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
celery_app = Celery('worker', broker=CELERY_BROKER)

@celery_app.task(name='tasks.generate_sticker')
def generate_sticker(task_id: str, image_url: str, reference_image_url: str | None, top_text: str | None, bottom_text: str | None):
    try:
        r1 = requests.get(image_url, timeout=30)
        r1.raise_for_status()
        input_bytes = r1.content

        reference_bytes = None
        if reference_image_url:
            r2 = requests.get(reference_image_url, timeout=30)
            r2.raise_for_status()
            reference_bytes = r2.content

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out_bytes = loop.run_until_complete(generate_sticker_from_image_bytes(input_bytes, top_text, bottom_text, reference_bytes))
        object_name = f"{task_id}.png"
        result_url = upload_bytes(out_bytes, object_name)

        with get_session() as s:
            t = s.get(Task, task_id)
            t.status = 'success'
            t.result_url = result_url
            s.add(t)
            s.commit()
    except Exception as e:
        with get_session() as s:
            t = s.get(Task, task_id)
            t.status = 'failed'
            t.error = str(e)
            s.add(t)
            s.commit()
