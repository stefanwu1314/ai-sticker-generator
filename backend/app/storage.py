import os
from minio import Minio
from urllib.parse import urljoin

MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS = os.getenv('MINIO_ACCESS', 'minioadmin')
MINIO_SECRET = os.getenv('MINIO_SECRET', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'generated')

minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

# ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)

def upload_bytes(data: bytes, object_name: str, content_type: str = 'image/png') -> str:
    from io import BytesIO
    bio = BytesIO(data)
    minio_client.put_object(MINIO_BUCKET, object_name, bio, length=len(data), content_type=content_type)
    # Return a presigned URL (1 hour)
    return minio_client.presigned_get_object(MINIO_BUCKET, object_name, expires=3600)
