import os
import shutil
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import HTTPException, UploadFile


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_task_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def safe_filename(filename: str) -> str:
    name = os.path.basename(filename)
    return name.replace(" ", "_")


def file_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_extension(filename: str, allowed_exts: Iterable[str], message: str) -> None:
    ext = file_ext(filename)
    if ext not in set(allowed_exts):
        raise HTTPException(status_code=400, detail=message)


async def save_upload_file(upload_file: UploadFile, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    with output_path.open("wb") as f:
        shutil.copyfileobj(upload_file.file, f)


def validate_file_size(file_path: Path, max_mb: int, file_kind: str) -> None:
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb <= 0:
        raise HTTPException(status_code=400, detail=f"{file_kind} file is empty")
    if size_mb > max_mb:
        raise HTTPException(
            status_code=400,
            detail=f"{file_kind} file too large: {size_mb:.2f}MB > {max_mb}MB",
        )
