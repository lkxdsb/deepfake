import threading
import time
from pathlib import Path
from typing import Any, Dict

import torch

from app.core.config import Settings
from audio.inference import (
    AudioDeepfakeInferenceEngine,
    AudioDependencyError,
    get_missing_audio_dependencies,
)


class AudioInferenceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_lock = threading.Lock()
        self.engine = AudioDeepfakeInferenceEngine(
            model_source=settings.audio_model_source,
            fake_threshold=settings.audio_fake_threshold,
            target_sr=settings.audio_sample_rate,
            device=self.device,
            cache_dir=settings.audio_model_cache_dir,
        )
        self.loaded = False
        self.model_name = self.engine.model_name

    def warmup(self) -> None:
        self.ensure_model_loaded()

    def ensure_model_loaded(self) -> None:
        if self.loaded:
            return
        with self._load_lock:
            if self.loaded:
                return
            self.engine.ensure_model_loaded()
            self.model_name = self.engine.model_name
            self.loaded = True

    def health(self) -> Dict[str, Any]:
        missing_dependencies = get_missing_audio_dependencies()
        return {
            "status": "ok",
            "model_loaded": bool(self.loaded),
            "device": str(self.device),
            "model_name": self.model_name,
            "dependencies_ready": not missing_dependencies,
            "missing_dependencies": missing_dependencies,
        }

    @torch.inference_mode()
    def predict_audio(self, audio_path: Path) -> Dict[str, Any]:
        try:
            self.ensure_model_loaded()
            t0 = time.perf_counter()
            output = self.engine.predict_file(audio_path)
            elapsed = time.perf_counter() - t0
        except AudioDependencyError as ex:
            raise RuntimeError(str(ex)) from ex

        output["inference_time"] = round(float(elapsed), 4)
        output["model_name"] = self.model_name
        output["bonafide_prob"] = output.get("real_prob")
        return output
