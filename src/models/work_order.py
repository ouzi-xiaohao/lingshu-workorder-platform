from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class WorkOrder(TimestampMixin, Base):
    __tablename__ = "work_orders"

    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    normalized_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="待识别", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="中", index=True)
    status: Mapped[str] = mapped_column(String(20), default="待识别", index=True)
    area: Mapped[str] = mapped_column(String(100), index=True)
    longitude: Mapped[float] = mapped_column(Float, default=121.4737)
    latitude: Mapped[float] = mapped_column(Float, default=31.2304)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sla_deadline: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)

    attachments: Mapped[list["Attachment"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")
    events: Mapped[list["WorkOrderEvent"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")


class Attachment(TimestampMixin, Base):
    __tablename__ = "work_order_attachments"

    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), index=True)
    media_type: Mapped[str] = mapped_column(String(20))
    object_key: Mapped[str] = mapped_column(String(300))
    original_name: Mapped[str] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(default=0)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_features: Mapped[str | None] = mapped_column(Text, nullable=True)

    work_order: Mapped[WorkOrder] = relationship(back_populates="attachments")


class WorkOrderEvent(TimestampMixin, Base):
    __tablename__ = "work_order_events"

    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(30), default="system")
    action: Mapped[str] = mapped_column(String(60), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    trace_id: Mapped[str] = mapped_column(String(64), index=True)

    work_order: Mapped[WorkOrder] = relationship(back_populates="events")
