"""Private, bounded storage for resident complaint photos."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


def upload_root() -> Path:
    configured = os.getenv("JALOS_UPLOAD_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / ".local" / "uploads"


def attachment_path(name: str) -> Path:
    # Database values are generated UUID basenames; reject any unexpected path.
    if Path(name).name != name or not name:
        raise HTTPException(404, "Complaint photo is unavailable")
    return upload_root() / name


async def store_complaint_photo(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower().split(";", maxsplit=1)[0].strip()
    if content_type not in PHOTO_TYPES and content_type != "application/octet-stream":
        raise HTTPException(415, "Attach a JPEG, PNG, or WebP image")

    parts: list[bytes] = []
    total = 0
    while chunk := await upload.read(64 * 1024):
        total += len(chunk)
        if total > MAX_PHOTO_BYTES:
            raise HTTPException(413, "Complaint photos must be 5 MB or smaller")
        parts.append(chunk)
    payload = b"".join(parts)
    image_type = next(
        (
            mime
            for mime, (_, signature_check) in PHOTO_TYPES.items()
            if signature_check(payload)
        ),
        None,
    )
    if not image_type or (content_type in PHOTO_TYPES and content_type != image_type):
        raise HTTPException(415, "The uploaded file is not a supported image")

    extension = PHOTO_TYPES[image_type][0]
    root = upload_root()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}{extension}"
    temporary_path = root / f".{name}.tmp"
    final_path = root / name
    try:
        temporary_path.write_bytes(payload)
        temporary_path.replace(final_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return name
