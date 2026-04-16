import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import get_services
from app.models.schemas import ChatRequest
from app.services.container import ServiceContainer


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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


@router.post("/stream")
def stream_chat(payload: ChatRequest, services: ServiceContainer = Depends(get_services)):
    history = [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in payload.history]

    def event_generator():
        try:
            yield _sse("start", {"model": services.settings.ai_chat_model})
            for event in services.chat_service.ask_stream(payload.question, history):
                yield _sse(event.get("type", "message"), event)
        except ValueError as ex:
            yield _sse("error", {"message": str(ex)})
        except RuntimeError as ex:
            yield _sse("error", {"message": str(ex)})
        except Exception as ex:
            yield _sse("error", {"message": f"chat failed: {ex}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
