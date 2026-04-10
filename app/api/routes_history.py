from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_services
from app.services.container import ServiceContainer


router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(services: ServiceContainer = Depends(get_services)):
    items = services.history_service.list_records(limit=200)
    return {"code": 0, "message": "success", "data": items}


@router.get("/{task_id}")
def history_detail(task_id: str, services: ServiceContainer = Depends(get_services)):
    row = services.history_service.get_record(task_id)
    batch_task_id = task_id
    if row is not None:
        batch_task_id = row.get("batch_task_id") or row["task_id"]

    rows = services.history_service.get_batch_records(batch_task_id)
    if not rows and row is None:
        return JSONResponse(status_code=404, content={"code": 1, "message": "task not found", "data": None})

    if not rows and row is not None:
        rows = [row]

    items = []
    for item_row in rows:
        items.append(
            {
                "record": item_row,
                "result": services.history_service.load_result_json(item_row["result_json_path"]),
            }
        )

    data = {
        "batch": services.history_service.build_batch_summary(rows),
        "items": items,
    }
    return {"code": 0, "message": "success", "data": data}
