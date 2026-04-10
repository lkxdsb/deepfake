import os
from dataclasses import dataclass
from pathlib import Path


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
    max_image_mb: int
    max_video_mb: int
    max_audio_mb: int
    demo_video_path: Path
    aasist_root: Path
    aasist_config_path: Path
    aasist_model_path: Path
    aasist_threshold: float

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
    def outputs_reports_dir(self) -> Path:
        return self.output_root / "reports"


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    output_root = Path(os.getenv("OUTPUT_ROOT", str(base_dir / "outputs"))).resolve()
    aasist_root = Path(os.getenv("AASIST_ROOT", str(base_dir / "aasist-main"))).resolve()

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
        max_image_mb=int(os.getenv("MAX_IMAGE_MB", "20")),
        max_video_mb=int(os.getenv("MAX_VIDEO_MB", "500")),
        max_audio_mb=int(os.getenv("MAX_AUDIO_MB", "100")),
        demo_video_path=Path(
            os.getenv(
                "DEMO_VIDEO_PATH",
                str(base_dir / "resources" / "videos" / "000_003.mp4"),
            )
        ).resolve(),
        aasist_root=aasist_root,
        aasist_config_path=Path(
            os.getenv(
                "AASIST_CONFIG_PATH",
                str(aasist_root / "config" / "AASIST-L.conf"),
            )
        ).resolve(),
        aasist_model_path=Path(
            os.getenv(
                "AASIST_MODEL_PATH",
                str(aasist_root / "exp_result" / "LA_AASIST-L_ep100_bs24" / "weights" / "best.pth"),
            )
        ).resolve(),
        aasist_threshold=float(os.getenv("AASIST_THRESHOLD", "1.8712")),
    )


settings = load_settings()
