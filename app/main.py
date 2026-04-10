import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_demo import router as demo_router
from app.api.routes_detect import router as detect_router
from app.api.routes_health import router as health_router
from app.api.routes_history import router as history_router
from app.api.routes_pages import router as pages_router
from app.core.config import settings
from app.core.logger import configure_logging
from app.services.container import build_services


configure_logging()

settings.output_root.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Deepfake Detection System",
    description="FastAPI + lightweight frontend MVP for deepfake detection demo",
    version="0.1.0",
)

services = build_services(settings)
app.state.services = services


@app.on_event("startup")
def startup_event() -> None:
    services.result_service.prepare_dirs()
    services.history_service.init_db()

    if settings.frontend_only:
        logging.info("Frontend-only mode enabled, skipping model warmup")
        return

    try:
        services.inference_service.warmup()
        logging.info("Model warmup completed")
    except Exception as ex:
        logging.exception("Model warmup failed: %s", ex)

    try:
        services.audio_inference_service.warmup()
        logging.info("Audio model warmup completed")
    except Exception as ex:
        logging.exception("Audio model warmup failed: %s", ex)


app.include_router(health_router)
app.include_router(detect_router)
app.include_router(history_router)
app.include_router(demo_router)
app.include_router(pages_router)

app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.mount("/outputs", StaticFiles(directory=str(settings.output_root)), name="outputs")
