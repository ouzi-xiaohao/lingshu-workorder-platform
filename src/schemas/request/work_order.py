from pydantic import BaseModel, Field


class AttachmentInput(BaseModel):
    media_type: str = Field(pattern="^(text|image|audio|video|file)$")
    object_key: str = Field(min_length=1, max_length=300)
    original_name: str = Field(min_length=1, max_length=200)
    size_bytes: int = Field(default=0, ge=0, le=100 * 1024 * 1024)


class WorkOrderCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=2, max_length=4000)
    area: str = Field(min_length=2, max_length=100)
    longitude: float = Field(default=121.4737, ge=-180, le=180)
    latitude: float = Field(default=31.2304, ge=-90, le=90)
    request_id: str | None = Field(default=None, max_length=80)
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=10)


class DispatchRequest(BaseModel):
    worker_id: int | None = None
    force: bool = False


class StatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(已接单|处理中|待回访|已完成|已取消)$")
    detail: str = Field(default="", max_length=1000)


class RatingRequest(BaseModel):
    score: float = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)
