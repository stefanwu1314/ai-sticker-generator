import os
import asyncio
import httpx
from celery import Celery
from .database import get_session
from .db import Task
from .storage import upload_bytes
from .model_client import generate_sticker_from_image_bytes

CELERY_BROKER = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
celery_app = Celery('worker', broker=CELERY_BROKER)


@celery_app.task(name='tasks.generate_sticker')
def generate_sticker(
    task_id: str,
    image_url: str,
    reference_image_url: str | None,
    top_text: str | None,
    bottom_text: str | None,
):
    try:
        input_bytes = _download(image_url)
        reference_bytes = _download(reference_image_url) if reference_image_url else None

        out_bytes = asyncio.run(
            generate_sticker_from_image_bytes(input_bytes, top_text, bottom_text, reference_bytes)
        )
        object_name = f"{task_id}.png"
        result_url = upload_bytes(out_bytes, object_name)

        with get_session() as s:
            t = s.get(Task, task_id)
            if t:
                t.status = 'success'
                t.result_url = result_url
                s.add(t)
                s.commit()
    except Exception as e:
        with get_session() as s:
            t = s.get(Task, task_id)
            if t:
                t.status = 'failed'
                t.error = str(e)[:1000]
                s.add(t)
                s.commit()


def _download(url: str) -> bytes:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content
