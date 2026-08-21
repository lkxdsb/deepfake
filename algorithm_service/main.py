import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.services.audio_inference_service import AudioInferenceService
from app.services.inference_service import InferenceService
from app.utils.vis_utils import build_explainability_panel


TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

app = FastAPI(
    title="Deepfake Algorithm Service",
    description="Internal inference-only API consumed by the Java business backend",
    version="1.0.0",
)

visual_inference = InferenceService(settings)
audio_inference = AudioInferenceService(settings)


@app.on_event("startup")
def startup_event() -> None:
    _prepare_output_dirs()
    if os.getenv("ALGORITHM_WARMUP", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    for name, service in (("visual", visual_inference), ("audio", audio_inference)):
        try:
            service.warmup()
            logging.info("%s model warmup completed", name)
        except Exception:
            logging.exception("%s model warmup failed", name)


@app.get("/v1/health")
def health() -> Dict[str, Any]:
    visual = visual_inference.health()
    audio = audio_inference.health()
    return {
        "status": "ok",
        "service": "python-algorithm",
        "model_loaded": visual.get("model_loaded", False),
        "model_name": visual.get("model_name"),
        "device": visual.get("device"),
        "audio_model_loaded": audio.get("model_loaded", False),
        "audio_model_name": audio.get("model_name"),
        "audio_device": audio.get("device"),
        "audio_dependencies_ready": audio.get("dependencies_ready", False),
        "audio_missing_dependencies": audio.get("missing_dependencies", []),
    }


@app.post("/v1/inference/image")
def infer_image(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    resolved_task_id = _task_id(task_id, "img")
    temp_path = _save_temporary_upload(file)
    try:
        output = visual_inference.predict_image(temp_path)
        heatmap_path = None
        if output.get("heatmap") is not None:
            image_bgr = cv2.cvtColor(output["image_rgb"], cv2.COLOR_RGB2BGR)
            panel = build_explainability_panel(
                image_bgr,
                output["heatmap"],
                bbox=output.get("face_bbox"),
                repeat=5,
            )
            heatmap_path = settings.outputs_heatmaps_dir / f"{resolved_task_id}.png"
            heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(heatmap_path), panel)

        return {
            "label": output["label"],
            "score": output["score"],
            "inference_time": output["inference_time"],
            "model_name": output["model_name"],
            "heatmap_url": _output_url(heatmap_path),
            "curve_url": None,
            "keyframes": [],
            "frame_results": [],
        }
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/v1/inference/video")
def infer_video(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    resolved_task_id = _task_id(task_id, "vid")
    temp_path = _save_temporary_upload(file)
    try:
        output = visual_inference.predict_video(temp_path, task_id=resolved_task_id)
        heatmap_path = _save_video_heatmap(resolved_task_id, output)
        return {
            "label": output["label"],
            "score": output["score"],
            "inference_time": output["inference_time"],
            "model_name": output["model_name"],
            "preview_url": _output_url(output.get("preview_path")),
            "preview_video_url": _output_url(output.get("preview_video_path")),
            "preview_duration_sec": output.get("preview_duration_sec"),
            "heatmap_url": _output_url(heatmap_path),
            "curve_url": _output_url(output.get("curve_path")),
            "keyframes": [_output_url(path) for path in output.get("keyframe_paths", [])],
            "frame_results": output.get("frame_results", []),
            "fps": output.get("fps"),
            "total_frames": output.get("total_frames"),
            "best_clip_index": output.get("best_clip_index"),
        }
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/v1/inference/audio")
def infer_audio(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    _task_id(task_id, "aud")
    temp_path = _save_temporary_upload(file)
    try:
        output = audio_inference.predict_audio(temp_path)
        return {
            "label": output["label"],
            "score": output["score"],
            "threshold": output.get("threshold"),
            "raw_score": output.get("raw_score"),
            "fake_prob": output.get("fake_prob"),
            "real_prob": output.get("real_prob"),
            "bonafide_prob": output.get("bonafide_prob"),
            "duration_sec": output.get("duration_sec"),
            "decision_rule": output.get("decision_rule"),
            "inference_time": output["inference_time"],
            "model_name": output["model_name"],
        }
    finally:
        temp_path.unlink(missing_ok=True)


def _save_video_heatmap(task_id: str, output: Dict[str, Any]) -> Optional[Path]:
    heatmap = output.get("attention_heatmap")
    frame = output.get("attention_frame_bgr")
    if heatmap is None or frame is None:
        return None
    panel = build_explainability_panel(
        frame,
        heatmap,
        bbox=output.get("attention_bbox"),
        repeat=5,
    )
    path = settings.outputs_heatmaps_dir / f"{task_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), panel)
    return path


def _task_id(candidate: Optional[str], prefix: str) -> str:
    if candidate is None or not candidate.strip():
        return f"{prefix}_{uuid4().hex[:12]}"
    candidate = candidate.strip()
    if not TASK_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=400, detail="invalid task_id")
    return candidate


def _save_temporary_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    with tempfile.NamedTemporaryFile(prefix="deepfake_algorithm_", suffix=suffix, delete=False) as target:
        shutil.copyfileobj(file.file, target)
        return Path(target.name)


def _prepare_output_dirs() -> None:
    for path in (
        settings.output_root,
        settings.outputs_heatmaps_dir,
        settings.outputs_frames_dir,
        settings.outputs_previews_dir,
        settings.outputs_reports_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _output_url(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    try:
        relative = Path(path).resolve().relative_to(settings.output_root.resolve())
    except ValueError:
        return None
    return "/outputs/" + relative.as_posix()
