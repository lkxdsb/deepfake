from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2

from app.services.history_service import HistoryService
from app.services.inference_service import InferenceService
from app.services.result_service import ResultService
from app.utils.vis_utils import build_explainability_panel


class ImageService:
    def __init__(
        self,
        inference_service: InferenceService,
        history_service: HistoryService,
        result_service: ResultService,
    ):
        self.inference_service = inference_service
        self.history_service = history_service
        self.result_service = result_service

    def detect(
        self,
        task_id: str,
        image_path: Path,
        file_name: str,
        batch_task_id: Optional[str] = None,
        batch_name: Optional[str] = None,
        batch_size: int = 1,
        batch_index: int = 1,
    ) -> Dict[str, Any]:
        infer = self.inference_service.predict_image(image_path)

        preview_path = image_path
        heatmap_path: Optional[Path] = None

        model_heatmap = infer.get("heatmap")
        if model_heatmap is not None:
            image_bgr = cv2.cvtColor(infer["image_rgb"], cv2.COLOR_RGB2BGR)
            panel = build_explainability_panel(image_bgr, model_heatmap, repeat=5)
            heatmap_path = self.result_service.settings.outputs_heatmaps_dir / f"{task_id}.png"
            heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(heatmap_path), panel)

        result_payload = {
            "task_id": task_id,
            "file_name": file_name,
            "file_type": "image",
            "label": infer["label"],
            "score": infer["score"],
            "inference_time": infer["inference_time"],
            "model_name": infer["model_name"],
            "preview_url": self.result_service.to_url(preview_path),
            "heatmap_url": self.result_service.to_url(heatmap_path),
            "curve_url": None,
            "keyframes": [],
            "frame_results": [],
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
                "file_type": "image",
                "result_label": infer["label"],
                "score": infer["score"],
                "source_path": str(image_path.resolve()),
                "result_json_path": str(result_json_path.resolve()),
                "preview_path": str(preview_path.resolve()),
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
