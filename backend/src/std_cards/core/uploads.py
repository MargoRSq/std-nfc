from fastapi import UploadFile

from std_cards.core.exceptions import ValidationFailedError

_CHUNK = 256 * 1024


async def read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile body in chunks, aborting as soon as ``max_bytes`` is
    exceeded — an oversized upload never fully buffers in memory."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise ValidationFailedError(message=f"Image too large (max {mb}MB)")
        chunks.append(chunk)
    return b"".join(chunks)
