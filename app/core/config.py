import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    base_dir: Path
    app_host: str
    app_port: int
    app_reload: bool
    frontend_only: bool
    model_cfg_path: Path
    model_ckpt_path: Path
    output_root: Path
    sqlite_path: Path
    score_threshold: float
    num_frames: int
    video_stride: float
    keyframe_count: int
    video_preview_seconds: float
    max_image_mb: int
    max_video_mb: int
    max_audio_mb: int
    demo_video_path: Path
    audio_model_source: str
    audio_model_cache_dir: Optional[Path]
    audio_fake_threshold: float
    audio_sample_rate: int

    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "app" / "templates"

    @property
    def static_dir(self) -> Path:
        return self.base_dir / "app" / "static"

    @property
    def outputs_uploads_dir(self) -> Path:
        return self.output_root / "uploads"

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
    base_dir = Path(__file__).resolve().parents[2]
    output_root = Path(os.getenv("OUTPUT_ROOT", str(base_dir / "outputs"))).resolve()
    audio_model_cache_dir_env = os.getenv("AUDIO_MODEL_CACHE_DIR")
    audio_model_cache_dir = (
        Path(audio_model_cache_dir_env).resolve() if audio_model_cache_dir_env else None
    )

    return Settings(
        base_dir=base_dir,
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        app_reload=_env_bool("APP_RELOAD", True),
        frontend_only=_env_bool("FRONTEND_ONLY", False),
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
        sqlite_path=Path(os.getenv("SQLITE_PATH", str(output_root / "app.db"))).resolve(),
        score_threshold=float(os.getenv("SCORE_THRESHOLD", "0.5")),
        num_frames=int(os.getenv("NUM_FRAMES", "10")),
        video_stride=float(os.getenv("VIDEO_STRIDE", "0.333")),
        keyframe_count=int(os.getenv("KEYFRAME_COUNT", "3")),
        video_preview_seconds=float(os.getenv("VIDEO_PREVIEW_SECONDS", "10")),
        max_image_mb=int(os.getenv("MAX_IMAGE_MB", "20")),
        max_video_mb=int(os.getenv("MAX_VIDEO_MB", "500")),
        max_audio_mb=int(os.getenv("MAX_AUDIO_MB", "100")),
        demo_video_path=Path(
            os.getenv(
                "DEMO_VIDEO_PATH",
                str(base_dir / "resources" / "videos" / "000_003.mp4"),
            )
        ).resolve(),
        audio_model_source=os.getenv("AUDIO_MODEL_SOURCE", "nii-yamagishilab/xls-r-1b-anti-deepfake"),
        audio_model_cache_dir=audio_model_cache_dir,
        audio_fake_threshold=float(os.getenv("AUDIO_FAKE_THRESHOLD", "0.5")),
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
    )


settings = load_settings()
