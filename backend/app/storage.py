import os
from io import BytesIO
from minio import Minio

# Internal endpoint is used by backend services (api/worker) inside the docker network,
# e.g. minio:9000. The external endpoint is used to build presigned URLs that browsers
# open, e.g. localhost:9000 (mapped by docker-compose port publishing).
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_EXTERNAL_ENDPOINT = os.getenv('MINIO_EXTERNAL_ENDPOINT', 'localhost:9000')
MINIO_ACCESS = os.getenv('MINIO_ACCESS', 'minioadmin')
MINIO_SECRET = os.getenv('MINIO_SECRET', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'generated')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
PRESIGN_EXPIRES = int(os.getenv('MINIO_PRESIGN_EXPIRES', '3600'))

minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=MINIO_SECURE)
external_client = (
    minio_client
    if MINIO_EXTERNAL_ENDPOINT == MINIO_ENDPOINT
    else Minio(MINIO_EXTERNAL_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=MINIO_SECURE)
)

_bucket_ready = False


def ensure_bucket() -> None:
    global _bucket_ready
    if _bucket_ready:
        return
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
    _bucket_ready = True


def upload_bytes(data: bytes, object_name: str, content_type: str = 'image/png') -> str:
    ensure_bucket()
    minio_client.put_object(MINIO_BUCKET, object_name, BytesIO(data), length=len(data), content_type=content_type)
    # Presigned URL built against the external endpoint so browsers can open it directly.
    return presigned_external_url(object_name)


def presigned_external_url(object_name: str) -> str:
    return external_client.presigned_get_object(MINIO_BUCKET, object_name, expires=PRESIGN_EXPIRES)


def internal_presigned_url(object_name: str) -> str:
    # Presigned URL built against the internal endpoint; used by the worker to fetch uploads.
    return minio_client.presigned_get_object(MINIO_BUCKET, object_name, expires=PRESIGN_EXPIRES)
