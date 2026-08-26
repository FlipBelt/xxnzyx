from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import uuid4

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig

from app.core.config import Settings, get_settings


class StorageConfigurationError(RuntimeError):
    """Raised when the selected object storage backend lacks required settings."""


@dataclass(frozen=True)
class StoredMedia:
    object_key: str
    public_url: str
    mime_type: str


def _safe_filename(filename: str | None) -> str:
    candidate = Path(filename or "upload").name
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip(".-")
    return candidate or "upload"


def _safe_object_key(key: str) -> str:
    normalized = PurePosixPath(key)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError("非法对象路径")
    return str(normalized)


class ObjectStorage:
    def upload_media(self, activity_id: int, filename: str | None, content: bytes, mime_type: str | None) -> StoredMedia:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings):
        self.root = settings.local_upload_dir

    def upload_media(self, activity_id: int, filename: str | None, content: bytes, mime_type: str | None) -> StoredMedia:
        safe_name = _safe_filename(filename)
        object_key = _safe_object_key(f"activity-media/{activity_id}/{uuid4().hex}-{safe_name}")
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        resolved_mime_type = mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        return StoredMedia(object_key=object_key, public_url=f"/uploads/{quote(object_key)}", mime_type=resolved_mime_type)


class CredentialProviderWrapper:
    """Adapter between Alibaba Cloud's ECS RAM role client and oss2's provider API."""

    def __init__(self, credential_client: CredentialClient):
        self.credential_client = credential_client

    def get_credentials(self):  # type: ignore[no-untyped-def]
        from oss2.credentials import Credentials

        credential = self.credential_client.get_credential()
        def value(name: str):  # type: ignore[no-untyped-def]
            getter = getattr(credential, f"get_{name}", None)
            return getter() if callable(getter) else getattr(credential, name)

        return Credentials(value("access_key_id"), value("access_key_secret"), value("security_token") or "")


class OssObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings):
        if not settings.oss_region or not settings.oss_bucket or not settings.oss_ram_role:
            raise StorageConfigurationError("OSS 存储需要配置 OSS_REGION、OSS_BUCKET 和 OSS_RAM_ROLE")

        import oss2

        endpoint = settings.oss_endpoint or f"https://oss-{settings.oss_region}-internal.aliyuncs.com"
        credential_client = CredentialClient(CredentialConfig(type="ecs_ram_role", role_name=settings.oss_ram_role))
        provider = CredentialProviderWrapper(credential_client)
        self.bucket = oss2.Bucket(oss2.ProviderAuth(provider), endpoint, settings.oss_bucket)
        self.prefix = settings.oss_object_prefix.strip("/")
        self.public_base_url = (settings.oss_public_base_url or f"https://{settings.oss_bucket}.oss-{settings.oss_region}.aliyuncs.com").rstrip("/")

    def upload_media(self, activity_id: int, filename: str | None, content: bytes, mime_type: str | None) -> StoredMedia:
        safe_name = _safe_filename(filename)
        prefix = f"{self.prefix}/" if self.prefix else ""
        object_key = _safe_object_key(f"{prefix}activity-media/{activity_id}/{uuid4().hex}-{safe_name}")
        resolved_mime_type = mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        self.bucket.put_object(object_key, content, headers={"Content-Type": resolved_mime_type})
        return StoredMedia(
            object_key=object_key,
            public_url=f"{self.public_base_url}/{quote(object_key)}",
            mime_type=resolved_mime_type,
        )


@lru_cache
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.storage_backend.lower() == "oss":
        return OssObjectStorage(settings)
    return LocalObjectStorage(settings)
