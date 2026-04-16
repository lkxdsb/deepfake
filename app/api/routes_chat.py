from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_services
from app.models.schemas import ChatRequest
from app.services.container import ServiceContainer


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask")
def ask_chat(payload: ChatRequest, services: ServiceContainer = Depends(get_services)):
    try:
        history = [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in payload.history]
        data = services.chat_service.ask(payload.question, history)
        return {"code": 0, "message": "success", "data": data}
    except ValueError as ex:
        return JSONResponse(status_code=400, content={"code": 1, "message": str(ex), "data": None})
    except RuntimeError as ex:
        return JSONResponse(status_code=503, content={"code": 1, "message": str(ex), "data": None})
    except Exception as ex:
        return JSONResponse(status_code=500, content={"code": 1, "message": f"chat failed: {ex}", "data": None})
