"""Bucket S3 compatible para fotos, firmas y PDF (E00-09).

Solo firma URLs y consulta objetos: quién puede subir o bajar qué lo deciden los servicios.
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    content_type: str
    size_bytes: int


class ObjectStorage:
    def __init__(self, client: S3Client, bucket: str, ttl_seconds: int) -> None:
        self._client = client
        self._bucket = bucket
        self._ttl = ttl_seconds

    def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
        """URL de PUT firmada. Tipo y tamaño van firmados: el bucket rechaza otro archivo."""
        return self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size_bytes,
            },
            ExpiresIn=self._ttl,
        )

    def download_url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=self._ttl
        )

    def ensure_bucket(self) -> bool:
        """Crea el bucket si no existe (MinIO local y tests). Devuelve si lo creó."""
        try:
            self._client.create_bucket(Bucket=self._bucket)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
                raise
            return False
        return True

    def delete(self, key: str) -> None:
        """Solo para el objeto de prueba de check_storage: los archivos reales no se borran."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    async def head(self, key: str) -> StoredObject | None:
        """Lo que hay en el bucket con esa clave, o None si no existe."""
        try:
            info = await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return StoredObject(content_type=info["ContentType"], size_bytes=info["ContentLength"])


def s3_client(endpoint_url: str, access_key: str, secret_key: str, region: str) -> S3Client:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        # Firma v4 y rutas con el bucket en el path: lo que aceptan MinIO y R2.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def build_storage(ttl_seconds: int | None = None) -> ObjectStorage:
    settings = get_settings()
    client = s3_client(
        settings.s3_endpoint_url, settings.s3_access_key, settings.s3_secret_key, settings.s3_region
    )
    ttl = settings.signed_url_ttl_seconds if ttl_seconds is None else ttl_seconds
    return ObjectStorage(client, settings.s3_bucket, ttl)


@lru_cache
def get_storage() -> ObjectStorage:
    return build_storage()
