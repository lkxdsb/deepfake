import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import Settings
from app.utils.file_utils import ensure_dir


class ResultService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def prepare_dirs(self) -> None:
        ensure_dir(self.settings.output_root)
        ensure_dir(self.settings.outputs_uploads_dir)
        ensure_dir(self.settings.outputs_heatmaps_dir)
        ensure_dir(self.settings.outputs_frames_dir)
        ensure_dir(self.settings.outputs_reports_dir)

    def save_result_json(self, task_id: str, data: Dict[str, Any]) -> Path:
        output = self.settings.outputs_reports_dir / f"{task_id}.json"
        ensure_dir(output.parent)
        with output.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output

    def to_url(self, file_path: Optional[Path]) -> Optional[str]:
        if file_path is None:
            return None
        try:
            rel = file_path.resolve().relative_to(self.settings.output_root.resolve())
        except ValueError:
            return None
        return "/outputs/" + str(rel).replace("\\", "/")
