import os
import re
import uuid

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def safe_filename(original: str) -> str:
    stem = os.path.splitext(os.path.basename(original))[0]
    stem = re.sub(r"[^\w\-]", "_", stem)[:64]
    return f"{stem}_{uuid.uuid4().hex}.pdf"


async def validate_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Solo file PDF sono accettati.")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Il file è vuoto.")

    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Il file supera il limite di {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Il file non è un PDF valido.")

    return content
