from pathlib import Path

from app.core.config import Settings
from app.services.storage import LocalObjectStorage


def test_local_storage_writes_safe_activity_media_path(tmp_path: Path) -> None:
    settings = Settings(local_upload_dir=tmp_path)
    storage = LocalObjectStorage(settings)

    stored = storage.upload_media(7, "demo 视频.mp4", b"video-bytes", "video/mp4")

    assert stored.object_key.startswith("activity-media/7/")
    assert stored.object_key.endswith("demo-.mp4")
    assert stored.public_url.startswith("/uploads/activity-media/7/")
    assert stored.mime_type == "video/mp4"
    assert (tmp_path / stored.object_key).read_bytes() == b"video-bytes"
