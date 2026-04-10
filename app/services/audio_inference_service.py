import json
import sys
import threading
import time
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch
import torch.nn.functional as F

from app.core.config import Settings

try:
    import librosa
except Exception:
    librosa = None


class AudioInferenceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_lock = threading.Lock()
        self.model = None
        self.model_config: Dict[str, Any] = {}
        self.loaded = False
        self.model_name = settings.aasist_model_path.name

    def _load_config(self) -> Dict[str, Any]:
        config_path = self.settings.aasist_config_path
        if not config_path.exists():
            raise FileNotFoundError(f"AASIST config not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize_state_dict(self, state: Any) -> Dict[str, Any]:
        if isinstance(state, dict) and "state_dict" in state and isinstance(state["state_dict"], dict):
            state = state["state_dict"]

        if not isinstance(state, dict):
            raise ValueError("invalid model checkpoint format")

        first_key = next(iter(state.keys()), "")
        if first_key.startswith("module."):
            state = {k.replace("module.", "", 1): v for k, v in state.items()}

        return state

    def _load_model(self) -> None:
        config = self._load_config()
        model_config = config.get("model_config", {})
        architecture = model_config.get("architecture")
        if not architecture:
            raise ValueError("missing model_config.architecture in AASIST config")

        aasist_root = self.settings.aasist_root
        if not aasist_root.exists():
            raise FileNotFoundError(f"AASIST root not found: {aasist_root}")

        aasist_root_str = str(aasist_root)
        if aasist_root_str not in sys.path:
            sys.path.insert(0, aasist_root_str)

        module = import_module(f"models.{architecture}")
        model_class = getattr(module, "Model")
        model = model_class(model_config).to(self.device)

        model_path = self.settings.aasist_model_path
        if not model_path.exists():
            raise FileNotFoundError(f"AASIST model not found: {model_path}")

        state = torch.load(model_path, map_location=self.device)
        model.load_state_dict(self._normalize_state_dict(state), strict=True)
        model.eval()

        self.model = model
        self.model_config = model_config
        self.model_name = model_path.name
        self.loaded = True

    def warmup(self) -> None:
        self.ensure_model_loaded()

    def ensure_model_loaded(self) -> None:
        if self.loaded:
            return
        with self._load_lock:
            if self.loaded:
                return
            self._load_model()

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_loaded": bool(self.loaded),
            "device": str(self.device),
            "model_name": self.model_name,
            "dependencies_ready": bool(librosa is not None),
        }

    @torch.inference_mode()
    def predict_audio(self, audio_path: Path) -> Dict[str, Any]:
        if librosa is None:
            raise RuntimeError("librosa is required for audio inference. Please install librosa and soundfile.")

        self.ensure_model_loaded()
        if self.model is None:
            raise RuntimeError("AASIST model is not loaded")

        target_sr = 16000
        nb_samp = int(self.model_config.get("nb_samp", 64600))

        waveform, _ = librosa.load(str(audio_path), sr=target_sr, mono=True)
        duration_sec = float(len(waveform) / float(target_sr)) if len(waveform) > 0 else 0.0

        if len(waveform) > nb_samp:
            waveform = waveform[:nb_samp]
        elif len(waveform) < nb_samp:
            pad = nb_samp - len(waveform)
            waveform = np.pad(waveform, (0, pad), mode="constant")

        input_tensor = torch.from_numpy(waveform).float().unsqueeze(0).to(self.device)

        t0 = time.perf_counter()
        _, batch_out = self.model(input_tensor)
        elapsed = time.perf_counter() - t0

        raw_score = float(batch_out[:, 1].item())
        class_prob = F.softmax(batch_out, dim=1)
        spoof_prob = float(class_prob[:, 0].item())
        bonafide_prob = float(class_prob[:, 1].item())

        threshold = float(self.settings.aasist_threshold)
        label = "fake" if raw_score < threshold else "real"

        return {
            "label": label,
            "score": spoof_prob,
            "inference_time": round(float(elapsed), 4),
            "model_name": self.model_name,
            "raw_score": raw_score,
            "threshold": threshold,
            "spoof_prob": spoof_prob,
            "bonafide_prob": bonafide_prob,
            "duration_sec": round(duration_sec, 4),
        }
