from dataclasses import dataclass

from app.core.config import Settings
from app.services.audio_inference_service import AudioInferenceService
from app.services.audio_service import AudioService
from app.services.history_service import HistoryService
from app.services.image_service import ImageService
from app.services.inference_service import InferenceService
from app.services.result_service import ResultService
from app.services.video_service import VideoService


@dataclass
class ServiceContainer:
    settings: Settings
    result_service: ResultService
    history_service: HistoryService
    inference_service: InferenceService
    audio_inference_service: AudioInferenceService
    image_service: ImageService
    video_service: VideoService
    audio_service: AudioService


def build_services(settings: Settings) -> ServiceContainer:
    result_service = ResultService(settings)
    history_service = HistoryService(settings.sqlite_path)
    inference_service = InferenceService(settings)
    audio_inference_service = AudioInferenceService(settings)
    image_service = ImageService(inference_service, history_service, result_service)
    video_service = VideoService(inference_service, history_service, result_service)
    audio_service = AudioService(audio_inference_service, history_service, result_service)

    return ServiceContainer(
        settings=settings,
        result_service=result_service,
        history_service=history_service,
        inference_service=inference_service,
        audio_inference_service=audio_inference_service,
        image_service=image_service,
        video_service=video_service,
        audio_service=audio_service,
    )
