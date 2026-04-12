import argparse
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import torch
import torch.nn.functional as F

try:
    import torchaudio
except Exception as ex:  # pragma: no cover - optional dependency at runtime
    torchaudio = None
    _TORCHAUDIO_IMPORT_ERROR = ex
else:
    _TORCHAUDIO_IMPORT_ERROR = None

try:
    from fairseq.models.wav2vec import Wav2Vec2Config, Wav2Vec2Model
except Exception as ex:  # pragma: no cover - optional dependency at runtime
    Wav2Vec2Config = None
    Wav2Vec2Model = None
    _FAIRSEQ_IMPORT_ERROR = ex
else:
    _FAIRSEQ_IMPORT_ERROR = None

try:
    from huggingface_hub import PyTorchModelHubMixin
except Exception as ex:  # pragma: no cover - optional dependency at runtime
    PyTorchModelHubMixin = None
    _HF_IMPORT_ERROR = ex
else:
    _HF_IMPORT_ERROR = None

try:
    from safetensors.torch import load_file as load_safetensors_file
except Exception:
    load_safetensors_file = None


DEFAULT_MODEL_SOURCE = "nii-yamagishilab/xls-r-1b-anti-deepfake"
AUDIO_FORMATS = (".mp3", ".wav", ".flac", ".m4a")
DEFAULT_SSL_CONFIG: Dict[str, Any] = {
    "quantize_targets": True,
    "extractor_mode": "layer_norm",
    "layer_norm_first": True,
    "final_dim": 1024,
    "latent_temp": (2.0, 0.1, 0.999995),
    "encoder_layerdrop": 0.0,
    "dropout_input": 0.0,
    "dropout_features": 0.0,
    "dropout": 0.0,
    "attention_dropout": 0.0,
    "conv_bias": True,
    "encoder_layers": 48,
    "encoder_embed_dim": 1280,
    "encoder_ffn_embed_dim": 5120,
    "encoder_attention_heads": 16,
    "feature_grad_mult": 1.0,
}


class AudioDependencyError(RuntimeError):
    pass


def get_missing_audio_dependencies() -> List[str]:
    missing = []
    if torchaudio is None:
        missing.append("torchaudio")
    if Wav2Vec2Config is None or Wav2Vec2Model is None:
        missing.append("fairseq")
    if PyTorchModelHubMixin is None:
        missing.append("huggingface_hub")
    return missing


def ensure_audio_dependencies() -> None:
    missing = get_missing_audio_dependencies()
    if not missing:
        return

    detail_parts = []
    if _TORCHAUDIO_IMPORT_ERROR is not None:
        detail_parts.append(f"torchaudio: {_TORCHAUDIO_IMPORT_ERROR}")
    if _FAIRSEQ_IMPORT_ERROR is not None:
        detail_parts.append(f"fairseq: {_FAIRSEQ_IMPORT_ERROR}")
    if _HF_IMPORT_ERROR is not None:
        detail_parts.append(f"huggingface_hub: {_HF_IMPORT_ERROR}")

    detail_text = "; ".join(detail_parts)
    raise AudioDependencyError(
        f"Missing audio deepfake dependencies: {', '.join(missing)}"
        + (f" ({detail_text})" if detail_text else "")
    )


ModelHubMixinBase = PyTorchModelHubMixin if PyTorchModelHubMixin is not None else object


def _build_ssl_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = dict(DEFAULT_SSL_CONFIG)
    if overrides:
        config.update(overrides)
    return config


def _resolve_model_name(model_source: Union[str, Path]) -> str:
    model_source = str(model_source)
    if os.path.exists(model_source):
        return Path(model_source).name
    return model_source


def _normalize_state_dict(state: Any) -> Dict[str, Any]:
    if isinstance(state, dict) and "state_dict" in state and isinstance(state["state_dict"], dict):
        state = state["state_dict"]

    if not isinstance(state, dict):
        raise AudioDependencyError("invalid audio checkpoint format")

    first_key = next(iter(state.keys()), "")
    if first_key.startswith("module."):
        state = {k.replace("module.", "", 1): v for k, v in state.items()}

    return state


def _load_state_dict_from_path(model_path: Path, device: torch.device) -> Dict[str, Any]:
    suffix = model_path.suffix.lower()
    if suffix == ".safetensors":
        if load_safetensors_file is None:
            raise AudioDependencyError(
                "safetensors is required when AUDIO_MODEL_SOURCE points to a .safetensors file"
            )
        state = load_safetensors_file(str(model_path), device=str(device))
    else:
        state = torch.load(str(model_path), map_location=device)
    return _normalize_state_dict(state)


def _infer_ssl_config_from_state_dict(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    ssl_config = dict(DEFAULT_SSL_CONFIG)

    mask_emb = state_dict.get("m_ssl.model.mask_emb")
    if mask_emb is None or mask_emb.ndim != 1:
        raise AudioDependencyError("unable to infer audio model architecture: missing m_ssl.model.mask_emb")
    embed_dim = int(mask_emb.shape[0])

    fc1_weight = state_dict.get("m_ssl.model.encoder.layers.0.fc1.weight")
    if fc1_weight is None or fc1_weight.ndim != 2:
        raise AudioDependencyError("unable to infer audio model architecture: missing encoder fc1 weights")
    ffn_dim = int(fc1_weight.shape[0])

    proj_fc_weight = state_dict.get("proj_fc.weight")
    if proj_fc_weight is None or proj_fc_weight.ndim != 2:
        raise AudioDependencyError("unable to infer audio model architecture: missing classifier weights")
    classifier_in_dim = int(proj_fc_weight.shape[1])

    pos_conv_weight_v = state_dict.get("m_ssl.model.encoder.pos_conv.0.weight_v")
    if pos_conv_weight_v is None or pos_conv_weight_v.ndim != 3:
        raise AudioDependencyError("unable to infer audio model architecture: missing positional conv weights")
    pos_conv_inner = int(pos_conv_weight_v.shape[1])
    attention_heads = max(1, embed_dim // pos_conv_inner)

    encoder_layer_ids = {
        int(match.group(1))
        for key in state_dict.keys()
        for match in [re.match(r"m_ssl\.model\.encoder\.layers\.(\d+)\.", key)]
        if match
    }
    encoder_layers = max(encoder_layer_ids) + 1 if encoder_layer_ids else int(DEFAULT_SSL_CONFIG["encoder_layers"])

    ssl_config.update(
        {
            "encoder_embed_dim": embed_dim,
            "encoder_ffn_embed_dim": ffn_dim,
            "encoder_attention_heads": attention_heads,
            "encoder_layers": encoder_layers,
        }
    )

    if classifier_in_dim != embed_dim:
        raise AudioDependencyError(
            f"classifier input dim ({classifier_in_dim}) does not match SSL embed dim ({embed_dim})"
        )

    return ssl_config


class SSLModel(torch.nn.Module):
    def __init__(self, ssl_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        ensure_audio_dependencies()
        self.ssl_config = _build_ssl_config(ssl_config)
        self.output_dim = int(self.ssl_config["encoder_embed_dim"])
        cfg = Wav2Vec2Config(**self.ssl_config)
        self.model = Wav2Vec2Model(cfg)

    def extract_feat(self, input_data: torch.Tensor, device: torch.device) -> torch.Tensor:
        if input_data.ndim == 3:
            input_data = input_data[:, :, 0]
        with torch.no_grad():
            features = self.model(
                input_data.to(device),
                mask=False,
                features_only=True,
            )["x"]
        return features


class DeepfakeDetector(torch.nn.Module, ModelHubMixinBase):
    def __init__(self, ssl_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.ssl_config = _build_ssl_config(ssl_config)
        self.ssl_orig_output_dim = int(self.ssl_config["encoder_embed_dim"])
        self.num_classes = 2
        self.m_ssl = SSLModel(self.ssl_config)
        self.adap_pool1d = torch.nn.AdaptiveAvgPool1d(output_size=1)
        self.proj_fc = torch.nn.Linear(
            in_features=self.ssl_orig_output_dim,
            out_features=self.num_classes,
        )

    def forward(self, wav: torch.Tensor) -> torch.Tensor:
        emb = self.m_ssl.extract_feat(wav, wav.device)
        emb = emb.transpose(1, 2)
        pooled_emb = self.adap_pool1d(emb).squeeze(-1)
        return self.proj_fc(pooled_emb)


def load_wav_and_preprocess(
    wav_path: Union[str, Path],
    target_sr: int = 16000,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    ensure_audio_dependencies()
    waveform, sample_rate = torchaudio.load(str(wav_path))
    if waveform.ndim == 2:
        waveform = waveform.mean(dim=0)
    waveform = waveform.to(torch.float32)
    if sample_rate != target_sr:
        waveform = torchaudio.functional.resample(waveform, sample_rate, target_sr)
    waveform = F.layer_norm(waveform, waveform.shape)
    if device is not None:
        waveform = waveform.to(device)
    return waveform.unsqueeze(0)


class AudioDeepfakeInferenceEngine:
    def __init__(
        self,
        model_source: Union[str, Path] = DEFAULT_MODEL_SOURCE,
        fake_threshold: float = 0.5,
        target_sr: int = 16000,
        device: Optional[torch.device] = None,
        cache_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.model_source = str(model_source)
        self.fake_threshold = float(fake_threshold)
        self.target_sr = int(target_sr)
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = str(cache_dir) if cache_dir else None
        self.model: Optional[DeepfakeDetector] = None
        self.model_name = _resolve_model_name(model_source)

    def ensure_model_loaded(self) -> None:
        if self.model is not None:
            return

        ensure_audio_dependencies()
        model_source_path = Path(self.model_source).expanduser()

        if model_source_path.is_file():
            state_dict = _load_state_dict_from_path(model_source_path, self.device)
            ssl_config = _infer_ssl_config_from_state_dict(state_dict)
            model = DeepfakeDetector(ssl_config=ssl_config)
            model.load_state_dict(state_dict, strict=True)
        else:
            load_kwargs: Dict[str, Any] = {}
            if self.cache_dir:
                load_kwargs["cache_dir"] = self.cache_dir
            model = DeepfakeDetector.from_pretrained(self.model_source, **load_kwargs)

        model.to(self.device)
        model.eval()
        self.model = model

    @torch.inference_mode()
    def predict_file(self, wav_path: Union[str, Path]) -> Dict[str, Any]:
        self.ensure_model_loaded()
        if self.model is None:
            raise RuntimeError("audio deepfake model is not loaded")

        waveform = load_wav_and_preprocess(wav_path, target_sr=self.target_sr, device=self.device)
        duration_sec = float(waveform.shape[-1] / float(self.target_sr)) if waveform.shape[-1] else 0.0
        logits = self.model(waveform)
        probs = F.softmax(logits, dim=1).squeeze(0)

        fake_prob = float(probs[0].item())
        real_prob = float(probs[1].item())
        predicted_index = int(torch.argmax(probs).item())
        predicted_prob = float(probs[predicted_index].item())
        label = "fake" if fake_prob >= self.fake_threshold else "real"

        return {
            "label": label,
            "score": fake_prob,
            "threshold": self.fake_threshold,
            "raw_score": fake_prob,
            "fake_prob": fake_prob,
            "real_prob": real_prob,
            "predicted_class_prob": predicted_prob,
            "duration_sec": round(duration_sec, 4),
            "decision_rule": "fake_prob >= threshold -> fake",
            "logits": [float(value) for value in logits.squeeze(0).tolist()],
        }


def run_folder_inference(
    folder_path: Union[str, Path],
    model_source: Union[str, Path] = DEFAULT_MODEL_SOURCE,
    fake_threshold: float = 0.5,
    audio_formats: Sequence[str] = AUDIO_FORMATS,
    device: Optional[torch.device] = None,
    cache_dir: Optional[Union[str, Path]] = None,
) -> List[Tuple[str, Dict[str, Any]]]:
    engine = AudioDeepfakeInferenceEngine(
        model_source=model_source,
        fake_threshold=fake_threshold,
        device=device,
        cache_dir=cache_dir,
    )
    results: List[Tuple[str, Dict[str, Any]]] = []

    for root, _, files in os.walk(str(folder_path)):
        for file_name in files:
            if not file_name.lower().endswith(tuple(audio_formats)):
                continue
            input_path = Path(root) / file_name
            results.append((file_name, engine.predict_file(input_path)))

    results.sort(key=lambda item: item[0])
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run audio deepfake inference on a folder of wav files.")
    parser.add_argument("folder_path", type=str, help="Folder containing audio files")
    parser.add_argument("--model-source", type=str, default=DEFAULT_MODEL_SOURCE)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--cache-dir", type=str, default=None)
    return parser.parse_args()


def _format_results(results: Iterable[Tuple[str, Dict[str, Any]]]) -> str:
    lines = ["", "=== Deepfake Detection Results ==="]
    for file_name, output in results:
        lines.append(
            f"{file_name}: label = {output['label']}, "
            f"fake prob = {output['fake_prob']:.3f}, real prob = {output['real_prob']:.3f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    args = _parse_args()
    chosen_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {chosen_device}")
    folder_results = run_folder_inference(
        folder_path=args.folder_path,
        model_source=args.model_source,
        fake_threshold=args.threshold,
        device=chosen_device,
        cache_dir=args.cache_dir,
    )
    print(_format_results(folder_results))
