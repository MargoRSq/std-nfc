import asyncio
import logging
import tempfile
from typing import BinaryIO

import boto3
from botocore.client import Config

from std_cards.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO.ENDPOINT,
            aws_access_key_id=settings.MINIO.ACCESS_KEY,
            aws_secret_access_key=settings.MINIO.SECRET_KEY,
            region_name=settings.MINIO.REGION,
            config=Config(signature_version="s3v4"),
        )

    async def upload(
        self,
        bucket: str,
        key: str,
        body: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=bucket, Key=key, Body=body, ContentType=content_type
            ),
        )

    async def download(self, bucket: str, key: str) -> bytes:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None, lambda: self._client.get_object(Bucket=bucket, Key=key)
        )
        return resp["Body"].read()

    async def delete(self, bucket: str, key: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._client.delete_object(Bucket=bucket, Key=key))

    async def presign_put(self, bucket: str, key: str, ttl_seconds: int = 300) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            ),
        )

    async def presign_get(self, bucket: str, key: str, ttl_seconds: int = 300) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            ),
        )

    async def stream_to_temp(self, bucket: str, key: str) -> str:
        """Download to /tmp, return path. For openpyxl read_only mode."""
        body = await self.download(bucket, key)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
            f.write(body)
            return f.name


_client: MinioClient | None = None


def get_minio() -> MinioClient:
    global _client
    if _client is None:
        _client = MinioClient()
    return _client
