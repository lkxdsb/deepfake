from dataclasses import dataclass
from typing import Any, Dict

from app.core.config import Settings
from app.services.audio_inference_service import AudioInferenceService
from app.services.audio_service import AudioService
from app.services.chat_service import ChatService
from app.services.history_service import HistoryService
from app.services.image_service import ImageService
from app.services.result_service import ResultService
from app.services.video_service import VideoService


class FrontendOnlyInferenceService:
    def __init__(self, model_name: str = "frontend-only") -> None:
        self.model_name = model_name

    def warmup(self) -> None:
        return None

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_loaded": False,
            "device": "disabled",
            "model_name": self.model_name,
            "frontend_only": True,
        }

    def predict_image(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        raise RuntimeError("Frontend-only mode enabled: image detection is disabled")

    def predict_video(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        raise RuntimeError("Frontend-only mode enabled: video detection is disabled")


class FrontendOnlyAudioInferenceService:
    def __init__(self, model_name: str = "frontend-only-audio") -> None:
        self.model_name = model_name

    def warmup(self) -> None:
        return None

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_loaded": False,
            "device": "disabled",
            "model_name": self.model_name,
            "dependencies_ready": False,
            "frontend_only": True,
        }

    def predict_audio(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        raise RuntimeError("Frontend-only mode enabled: audio detection is disabled")


@dataclass
class ServiceContainer:
    settings: Settings
    result_service: ResultService
    history_service: HistoryService
    inference_service: Any
    audio_inference_service: Any
    image_service: ImageService
    video_service: VideoService
    audio_service: AudioService
    chat_service: ChatService


def build_services(settings: Settings) -> ServiceContainer:
    result_service = ResultService(settings)
    history_service = HistoryService(settings.sqlite_path)

    if settings.frontend_only:
        inference_service = FrontendOnlyInferenceService()
        audio_inference_service = FrontendOnlyAudioInferenceService()
    else:
        from app.services.inference_service import InferenceService

        inference_service = InferenceService(settings)
        audio_inference_service = AudioInferenceService(settings)

    image_service = ImageService(inference_service, history_service, result_service)
    video_service = VideoService(inference_service, history_service, result_service)
    audio_service = AudioService(audio_inference_service, history_service, result_service)
    chat_service = ChatService(settings)

    return ServiceContainer(
        settings=settings,
        result_service=result_service,
        history_service=history_service,
        inference_service=inference_service,
        audio_inference_service=audio_inference_service,
        image_service=image_service,
        video_service=video_service,
        audio_service=audio_service,
        chat_service=chat_service,
    )
