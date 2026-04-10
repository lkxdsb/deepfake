from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_services
from app.services.container import ServiceContainer
from app.utils.file_utils import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    build_task_id,
    safe_filename,
    save_upload_file,
    validate_extension,
    validate_file_size,
)


router = APIRouter(prefix="/api/detect", tags=["detect"])


def _error_response(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": 1, "message": message, "data": None})


def _normalize_uploads(file: Optional[UploadFile], files: Optional[List[UploadFile]]) -> List[UploadFile]:
    uploads: List[UploadFile] = []
    if file is not None and file.filename:
        uploads.append(file)
    if files:
        uploads.extend([item for item in files if item is not None and item.filename])
    return uploads


def _resolve_batch_name(batch_name: Optional[str], media_label: str, total_count: int) -> Optional[str]:
    cleaned = (batch_name or "").strip()
    if cleaned:
        return cleaned
    if total_count <= 1:
        return None
    timestamp = datetime.now().strftime("%m-%d %H:%M")
    return f"{media_label}批量任务 {timestamp}"


def _build_batch_response(results: List[Dict], batch_task_id: str, batch_name: Optional[str]) -> Dict:
    return {
        "batch_task_id": batch_task_id,
        "batch_name": batch_name,
        "batch_size": len(results),
        "file_type": results[0]["file_type"] if results else None,
        "task_ids": [item["task_id"] for item in results],
        "items": [
            {
                "task_id": item["task_id"],
                "file_name": item["file_name"],
                "label": item["label"],
                "score": item["score"],
            }
            for item in results
        ],
    }


@router.post("/image")
async def detect_image(
    file: Optional[UploadFile] = File(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    batch_name: Optional[str] = Form(default=None),
    services: ServiceContainer = Depends(get_services),
):
    uploads = _normalize_uploads(file, files)
    if not uploads:
        return _error_response("image file is required")

    try:
        for upload in uploads:
            validate_extension(upload.filename, IMAGE_EXTENSIONS, "unsupported image format, use jpg/jpeg/png")

        resolved_batch_name = _resolve_batch_name(batch_name, "图片", len(uploads))
        batch_task_id = build_task_id("imgbatch") if len(uploads) > 1 else None
        results = []

        for index, upload in enumerate(uploads, start=1):
            task_id = build_task_id("img")
            out_name = f"{task_id}_{safe_filename(upload.filename)}"
            save_path = services.settings.outputs_uploads_dir / out_name
            await save_upload_file(upload, save_path)
            validate_file_size(save_path, services.settings.max_image_mb, "image")
            results.append(
                services.image_service.detect(
                    task_id=task_id,
                    image_path=Path(save_path),
                    file_name=upload.filename,
                    batch_task_id=batch_task_id,
                    batch_name=resolved_batch_name,
                    batch_size=len(uploads),
                    batch_index=index,
                )
            )

        data = results[0] if len(results) == 1 else _build_batch_response(results, batch_task_id, resolved_batch_name)
        return {"code": 0, "message": "success", "data": data}
    except HTTPException as ex:
        return _error_response(ex.detail, status_code=ex.status_code)
    except Exception as ex:
        return _error_response(f"image detect failed: {ex}", status_code=500)


@router.post("/video")
async def detect_video(
    file: Optional[UploadFile] = File(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    batch_name: Optional[str] = Form(default=None),
    services: ServiceContainer = Depends(get_services),
):
    uploads = _normalize_uploads(file, files)
    if not uploads:
        return _error_response("video file is required")

    try:
        for upload in uploads:
            validate_extension(upload.filename, VIDEO_EXTENSIONS, "unsupported video format, use mp4/avi/mov/mkv")

        resolved_batch_name = _resolve_batch_name(batch_name, "视频", len(uploads))
        batch_task_id = build_task_id("vidbatch") if len(uploads) > 1 else None
        results = []

        for index, upload in enumerate(uploads, start=1):
            task_id = build_task_id("vid")
            out_name = f"{task_id}_{safe_filename(upload.filename)}"
            save_path = services.settings.outputs_uploads_dir / out_name
            await save_upload_file(upload, save_path)
            validate_file_size(save_path, services.settings.max_video_mb, "video")
            results.append(
                services.video_service.detect(
                    task_id=task_id,
                    video_path=Path(save_path),
                    file_name=upload.filename,
                    batch_task_id=batch_task_id,
                    batch_name=resolved_batch_name,
                    batch_size=len(uploads),
                    batch_index=index,
                )
            )

        data = results[0] if len(results) == 1 else _build_batch_response(results, batch_task_id, resolved_batch_name)
        return {"code": 0, "message": "success", "data": data}
    except HTTPException as ex:
        return _error_response(ex.detail, status_code=ex.status_code)
    except Exception as ex:
        return _error_response(f"video detect failed: {ex}", status_code=500)


@router.post("/audio")
async def detect_audio(
    file: Optional[UploadFile] = File(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    batch_name: Optional[str] = Form(default=None),
    services: ServiceContainer = Depends(get_services),
):
    uploads = _normalize_uploads(file, files)
    if not uploads:
        return _error_response("audio file is required")

    try:
        for upload in uploads:
            validate_extension(upload.filename, AUDIO_EXTENSIONS, "unsupported audio format, use wav/mp3/flac")

        resolved_batch_name = _resolve_batch_name(batch_name, "音频", len(uploads))
        batch_task_id = build_task_id("audbatch") if len(uploads) > 1 else None
        results = []

        for index, upload in enumerate(uploads, start=1):
            task_id = build_task_id("aud")
            out_name = f"{task_id}_{safe_filename(upload.filename)}"
            save_path = services.settings.outputs_uploads_dir / out_name
            await save_upload_file(upload, save_path)
            validate_file_size(save_path, services.settings.max_audio_mb, "audio")
            results.append(
                services.audio_service.detect(
                    task_id=task_id,
                    audio_path=Path(save_path),
                    file_name=upload.filename,
                    batch_task_id=batch_task_id,
                    batch_name=resolved_batch_name,
                    batch_size=len(uploads),
                    batch_index=index,
                )
            )

        data = results[0] if len(results) == 1 else _build_batch_response(results, batch_task_id, resolved_batch_name)
        return {"code": 0, "message": "success", "data": data}
    except HTTPException as ex:
        return _error_response(ex.detail, status_code=ex.status_code)
    except Exception as ex:
        return _error_response(f"audio detect failed: {ex}", status_code=500)
