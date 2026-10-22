import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
CONTENT_TYPE_EXT = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def upload_root() -> Path:
    root = Path(settings.upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def detect_type(data: bytes) -> str | None:
    """Detect the real file type from its magic bytes (never trust the extension or Content-Type header)."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def clean_filename(name: str | None) -> str:
    name = (name or "document").replace("\\", "/").split("/")[-1]  # basename only
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return (name or "document")[:200]


async def validate_and_save(file: UploadFile) -> tuple[str, str, str, int]:
    """Returns (original_filename, stored_filename, content_type, size). Raises HTTPException when invalid."""
    original = clean_filename(file.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"'{original}': only PDF, JPG, JPEG and PNG files are allowed.")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"'{original}' is larger than {settings.max_upload_mb} MB.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail=f"'{original}' is empty.")
    real_type = detect_type(data)
    if real_type is None or ALLOWED_EXTENSIONS[ext] != real_type:
        raise HTTPException(status_code=400, detail=f"'{original}' content does not match a valid PDF, JPG or PNG file.")
    stored = f"{uuid.uuid4().hex}{CONTENT_TYPE_EXT[real_type]}"
    root = upload_root()
    target = (root / stored).resolve()
    if target.parent != root:  # path traversal guard
        raise HTTPException(status_code=400, detail="Invalid file name.")
    target.write_bytes(data)
    return original, stored, real_type, len(data)


def stored_path(stored_filename: str) -> Path:
    root = upload_root()
    path = (root / stored_filename).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found.")
    return path
