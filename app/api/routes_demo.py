from pathlib import Path

import cv2
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_services
from app.services.container import ServiceContainer
from app.utils.file_utils import build_task_id


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/run")
def run_demo(mode: str = "video", services: ServiceContainer = Depends(get_services)):
    demo_video = Path(services.settings.demo_video_path)
    if not demo_video.exists():
        return JSONResponse(status_code=404, content={"code": 1, "message": f"demo video not found: {demo_video}", "data": None})

    try:
        if mode == "image":
            cap = cv2.VideoCapture(str(demo_video))
            ok, frame = cap.read()
            cap.release()
            if not ok:
                raise ValueError("unable to decode frame from demo video")

            task_id = build_task_id("imgdemo")
            img_path = services.settings.outputs_uploads_dir / f"{task_id}_demo.jpg"
            img_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(img_path), frame)

            data = services.image_service.detect(task_id=task_id, image_path=img_path, file_name=img_path.name)
            return {"code": 0, "message": "success", "data": data}

        task_id = build_task_id("viddemo")
        data = services.video_service.detect(task_id=task_id, video_path=demo_video, file_name=demo_video.name)
        return {"code": 0, "message": "success", "data": data}
    except Exception as ex:
        return JSONResponse(status_code=500, content={"code": 1, "message": f"demo run failed: {ex}", "data": None})
