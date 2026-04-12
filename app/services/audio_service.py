from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.audio_inference_service import AudioInferenceService
from app.services.history_service import HistoryService
from app.services.result_service import ResultService


class AudioService:
    def __init__(
        self,
        audio_inference_service: AudioInferenceService,
        history_service: HistoryService,
        result_service: ResultService,
    ):
        self.audio_inference_service = audio_inference_service
        self.history_service = history_service
        self.result_service = result_service

    def detect(
        self,
        task_id: str,
        audio_path: Path,
        file_name: str,
        batch_task_id: Optional[str] = None,
        batch_name: Optional[str] = None,
        batch_size: int = 1,
        batch_index: int = 1,
    ) -> Dict[str, Any]:
        infer = self.audio_inference_service.predict_audio(audio_path)

        preview_url = self.result_service.to_url(audio_path)
        result_payload = {
            "task_id": task_id,
            "file_name": file_name,
            "file_type": "audio",
            "label": infer["label"],
            "score": infer["score"],
            "inference_time": infer["inference_time"],
            "model_name": infer["model_name"],
            "preview_url": preview_url,
            "heatmap_url": None,
            "curve_url": None,
            "keyframes": [],
            "frame_results": [],
            "raw_score": infer.get("raw_score"),
            "threshold": infer.get("threshold"),
            "duration_sec": infer.get("duration_sec"),
            "spoof_prob": infer.get("spoof_prob", infer.get("fake_prob")),
            "fake_prob": infer.get("fake_prob", infer.get("spoof_prob")),
            "bonafide_prob": infer.get("bonafide_prob", infer.get("real_prob")),
            "real_prob": infer.get("real_prob", infer.get("bonafide_prob")),
            "decision_rule": infer.get("decision_rule"),
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
                "file_type": "audio",
                "result_label": infer["label"],
                "score": infer["score"],
                "source_path": str(audio_path.resolve()),
                "result_json_path": str(result_json_path.resolve()),
                "preview_path": str(audio_path.resolve()),
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
