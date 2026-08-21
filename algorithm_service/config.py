import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    model_cfg_path: Path
    model_ckpt_path: Path
    output_root: Path
    score_threshold: float
    num_frames: int
    video_stride: float
    keyframe_count: int
    video_preview_seconds: float
    audio_model_source: str
    audio_model_cache_dir: Optional[Path]
    audio_fake_threshold: float
    audio_sample_rate: int

    @property
    def outputs_heatmaps_dir(self) -> Path:
        return self.output_root / "heatmaps"

    @property
    def outputs_frames_dir(self) -> Path:
        return self.output_root / "frames"

    @property
    def outputs_previews_dir(self) -> Path:
        return self.output_root / "previews"

    @property
    def outputs_reports_dir(self) -> Path:
        return self.output_root / "reports"


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[1]
    output_root = Path(os.getenv("OUTPUT_ROOT", str(base_dir / "outputs-java"))).resolve()
    audio_cache = os.getenv("AUDIO_MODEL_CACHE_DIR")

    return Settings(
        base_dir=base_dir,
        model_cfg_path=Path(
            os.getenv(
                "MODEL_CFG_PATH",
                str(base_dir / "logs" / "DFD-FCG" / "na2vi8su" / "setting.yaml"),
            )
        ).resolve(),
        model_ckpt_path=Path(
            os.getenv(
                "MODEL_CKPT_PATH",
                str(
                    base_dir
                    / "logs"
                    / "DFD-FCG"
                    / "na2vi8su"
                    / "checkpoints"
                    / "epoch=29-step=33540.ckpt"
                ),
            )
        ).resolve(),
        output_root=output_root,
        score_threshold=float(os.getenv("SCORE_THRESHOLD", "0.5")),
        num_frames=int(os.getenv("NUM_FRAMES", "10")),
        video_stride=float(os.getenv("VIDEO_STRIDE", "0.333")),
        keyframe_count=int(os.getenv("KEYFRAME_COUNT", "3")),
        video_preview_seconds=float(os.getenv("VIDEO_PREVIEW_SECONDS", "10")),
        audio_model_source=os.getenv(
            "AUDIO_MODEL_SOURCE",
            "nii-yamagishilab/xls-r-1b-anti-deepfake",
        ),
        audio_model_cache_dir=Path(audio_cache).resolve() if audio_cache else None,
        audio_fake_threshold=float(os.getenv("AUDIO_FAKE_THRESHOLD", "0.5")),
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
    )


settings = load_settings()
