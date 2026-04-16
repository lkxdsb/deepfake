from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Dict[str, Any]] = None


class DetectionResult(BaseModel):
    task_id: str
    file_name: str
    file_type: str
    label: str
    score: float
    inference_time: float
    model_name: str
    preview_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    preview_duration_sec: Optional[float] = None
    heatmap_url: Optional[str] = None
    curve_url: Optional[str] = None
    keyframes: List[str] = Field(default_factory=list)
    frame_results: List[Dict[str, Any]] = Field(default_factory=list)
    batch_task_id: Optional[str] = None
    batch_name: Optional[str] = None
    batch_size: int = 1
    batch_index: int = 1


class HistoryItem(BaseModel):
    task_id: str
    batch_name: str
    file_type: str
    item_count: int
    fake_count: int
    avg_score: float
    total_inference_time: float
    created_at: str


class HistoryDetail(BaseModel):
    batch: Dict[str, Any]
    items: List[Dict[str, Any]]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: List[ChatMessage] = Field(default_factory=list)
