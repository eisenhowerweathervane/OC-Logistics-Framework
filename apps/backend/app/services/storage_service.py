import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    client = _get_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=settings.s3_bucket)
            logger.info("created_bucket", bucket=settings.s3_bucket)
        else:
            raise


def generate_storage_key(org_id: str, folder: str, filename: str) -> str:
    safe_filename = filename.replace(" ", "_")
    unique = uuid.uuid4().hex[:8]
    return f"{org_id}/{folder}/{unique}_{safe_filename}"


def presign_upload(storage_key: str, mime_type: str) -> str:
    client = _get_client()
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": storage_key,
            "ContentType": mime_type,
        },
        ExpiresIn=settings.presign_expiry_seconds,
    )
    return url


def presign_download(storage_key: str) -> str:
    client = _get_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": storage_key},
        ExpiresIn=settings.presign_expiry_seconds,
    )
    return url


def check_health() -> bool:
    try:
        client = _get_client()
        client.head_bucket(Bucket=settings.s3_bucket)
        return True
    except Exception:
        return False
