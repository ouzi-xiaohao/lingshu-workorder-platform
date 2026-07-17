from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttachmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media_type: str
    object_key: str
    original_name: str
    size_bytes: int
    transcript: str | None = None
    detected_features: str | None = None


class EventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action: str
    actor_type: str
    from_status: str | None
    to_status: str | None
    detail: str
    created_at: datetime


class WorkOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    title: str
    category: str
    priority: str
    status: str
    area: str
    reporter_id: int
    assignee_id: int | None
    confidence: float
    sla_deadline: datetime | None
    created_at: datetime


class WorkOrderDetail(WorkOrderSummary):
    description: str
    normalized_summary: str | None
    longitude: float
    latitude: float
    rating: float | None
    trace_id: str
    attachments: list[AttachmentView] = Field(default_factory=list)
    events: list[EventView] = Field(default_factory=list)
