from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_services
from app.content.education_content import (
    EDUCATION_TRACKS,
    QUIZ_BADGES,
    QUIZ_QUESTIONS,
    RESOURCE_GROUPS,
    SCAM_SCENARIOS,
    SPOTTING_SIGNALS,
    VERIFICATION_STEPS,
)
from app.services.container import ServiceContainer


router = APIRouter(tags=["pages"])


def get_templates(services: ServiceContainer) -> Jinja2Templates:
    return Jinja2Templates(directory=str(services.settings.templates_dir))


@router.get("/", response_class=HTMLResponse)
def page_index(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    history_summary = services.history_service.get_history_summary(recent_limit=10)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "demo_video": str(services.settings.demo_video_path.name),
            "history_summary": history_summary,
            "ai_chat_ready": services.chat_service.is_ready(),
            "ai_chat_model": services.settings.ai_chat_model,
        },
    )


@router.get("/chat", response_class=HTMLResponse)
def page_chat(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "ai_chat_ready": services.chat_service.is_ready(),
        },
    )


@router.get("/education", response_class=HTMLResponse)
def page_education(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse(
        "education.html",
        {
            "request": request,
            "education_tracks": EDUCATION_TRACKS,
            "scam_scenarios": SCAM_SCENARIOS,
            "spotting_signals": SPOTTING_SIGNALS,
            "verification_steps": VERIFICATION_STEPS,
            "resource_groups": RESOURCE_GROUPS,
            "quiz_question_count": len(QUIZ_QUESTIONS),
        },
    )


@router.get("/quiz", response_class=HTMLResponse)
def page_quiz(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse(
        "quiz.html",
        {
            "request": request,
            "quiz_questions": QUIZ_QUESTIONS,
            "quiz_badges": QUIZ_BADGES,
        },
    )


@router.get("/detect/image", response_class=HTMLResponse)
def page_detect_image(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse("detect_image.html", {"request": request})


@router.get("/detect/video", response_class=HTMLResponse)
def page_detect_video(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse("detect_video.html", {"request": request})


@router.get("/detect/audio", response_class=HTMLResponse)
def page_detect_audio(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    return templates.TemplateResponse("detect_audio.html", {"request": request})


@router.get("/results/{task_id}", response_class=HTMLResponse)
def page_result(
    task_id: str,
    request: Request,
    index: Optional[int] = Query(default=None, ge=0),
    services: ServiceContainer = Depends(get_services),
):
    templates = get_templates(services)
    row = services.history_service.get_record(task_id)
    batch_task_id = task_id
    selected_task_id = None

    if row is not None:
        batch_task_id = row.get("batch_task_id") or row["task_id"]
        selected_task_id = row["task_id"]

    rows = services.history_service.get_batch_records(batch_task_id)
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

    batch = services.history_service.build_batch_summary(rows)
    initial_index = 0
    if items:
        if index is not None:
            initial_index = max(0, min(index, len(items) - 1))
        elif selected_task_id is not None:
            for idx, item in enumerate(items):
                if item["record"]["task_id"] == selected_task_id:
                    initial_index = idx
                    break

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "task_id": task_id,
            "batch": batch,
            "items": items,
            "initial_index": initial_index,
        },
    )


@router.get("/history", response_class=HTMLResponse)
def page_history(request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    items = services.history_service.list_records(limit=200)
    history_summary = services.history_service.get_history_summary(recent_limit=20)
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "items": items,
            "history_summary": history_summary,
        },
    )


@router.get("/history/{task_id}", response_class=HTMLResponse)
def page_history_detail(task_id: str, request: Request, services: ServiceContainer = Depends(get_services)):
    templates = get_templates(services)
    row = services.history_service.get_record(task_id)
    batch_task_id = task_id
    if row is not None:
        batch_task_id = row.get("batch_task_id") or row["task_id"]

    rows = services.history_service.get_batch_records(batch_task_id)
    if not rows and row is not None:
        rows = [row]

    batch = services.history_service.build_batch_summary(rows)
    analytics = services.history_service.build_batch_analytics(rows)
    items = []
    for item_row in rows:
        items.append(
            {
                "record": item_row,
                "result": services.history_service.load_result_json(item_row["result_json_path"]),
            }
        )

    return templates.TemplateResponse(
        "history_detail.html",
        {
            "request": request,
            "task_id": task_id,
            "batch": batch,
            "items": items,
            "analytics": analytics,
        },
    )
