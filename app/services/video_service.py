from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import cv2

from app.services.history_service import HistoryService
from app.services.result_service import ResultService
from app.utils.vis_utils import build_explainability_panel

if TYPE_CHECKING:
    from app.services.inference_service import InferenceService


class VideoService:
    def __init__(
        self,
        inference_service: "InferenceService",
        history_service: HistoryService,
        result_service: ResultService,
    ):
        self.inference_service = inference_service
        self.history_service = history_service
        self.result_service = result_service

    def detect(
        self,
        task_id: str,
        video_path: Path,
        file_name: str,
        batch_task_id: Optional[str] = None,
        batch_name: Optional[str] = None,
        batch_size: int = 1,
        batch_index: int = 1,
    ) -> Dict[str, Any]:
        infer = self.inference_service.predict_video(video_path, task_id=task_id)

        keyframe_urls = [self.result_service.to_url(p) for p in infer["keyframe_paths"] if p is not None]
        preview_url = self.result_service.to_url(infer.get("preview_path"))
        curve_url = self.result_service.to_url(infer.get("curve_path"))

        heatmap_path: Optional[Path] = None
        model_heatmap = infer.get("attention_heatmap")
        preview_path = infer.get("preview_path")
        if model_heatmap is not None and preview_path is not None and Path(preview_path).exists():
            preview_img = cv2.imread(str(preview_path))
            if preview_img is not None:
                panel = build_explainability_panel(
                    preview_img,
                    model_heatmap,
                    bbox=infer.get("attention_bbox"),
                    repeat=5,
                )
                heatmap_path = self.result_service.settings.outputs_heatmaps_dir / f"{task_id}.png"
                heatmap_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(heatmap_path), panel)

        result_payload = {
            "task_id": task_id,
            "file_name": file_name,
            "file_type": "video",
            "label": infer["label"],
            "score": infer["score"],
            "inference_time": infer["inference_time"],
            "model_name": infer["model_name"],
            "preview_url": preview_url,
            "heatmap_url": self.result_service.to_url(heatmap_path),
            "curve_url": curve_url,
            "keyframes": keyframe_urls,
            "frame_results": infer["frame_results"],
            "fps": infer["fps"],
            "total_frames": infer["total_frames"],
            "best_clip_index": infer.get("best_clip_index"),
            "batch_task_id": batch_task_id or task_id,
            "batch_name": batch_name or file_name,
            "batch_size": batch_size,
            "batch_index": batch_index,
        }

        result_json_path = self.result_service.save_result_json(task_id, result_payload)

        self.history_service.save_record(
            {
                "task_id": task_id,
                "file_name": file_name,
                "file_type": "video",
                "result_label": infer["label"],
                "score": infer["score"],
                "source_path": str(video_path.resolve()),
                "result_json_path": str(result_json_path.resolve()),
                "preview_path": str((infer.get("preview_path") or video_path).resolve()),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "model_version": infer["model_name"],
                "inference_time": infer["inference_time"],
                "batch_task_id": batch_task_id or task_id,
                "batch_name": batch_name or file_name,
                "batch_size": batch_size,
                "batch_index": batch_index,
            }
        )

        return result_payload
