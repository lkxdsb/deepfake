from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(services: ServiceContainer = Depends(get_services)):
    payload = services.inference_service.health()
    audio_health = services.audio_inference_service.health()

    payload["audio_model_loaded"] = audio_health["model_loaded"]
    payload["audio_model_name"] = audio_health["model_name"]
    payload["audio_device"] = audio_health["device"]
    payload["audio_dependencies_ready"] = audio_health.get("dependencies_ready", False)
    payload["audio_missing_dependencies"] = audio_health.get("missing_dependencies", [])

    return payload
