from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(180))
    display_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20), default="resident", index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    area: Mapped[str] = mapped_column(String(80), default="全园区")
    is_active: Mapped[bool] = mapped_column(default=True)
    credit_balance: Mapped[int] = mapped_column(Integer, default=0)

    worker_profile: Mapped["WorkerProfile | None"] = relationship(back_populates="user", uselist=False)


class WorkerProfile(TimestampMixin, Base):
    __tablename__ = "worker_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    skills: Mapped[str] = mapped_column(String(300), default="综合服务")
    longitude: Mapped[float] = mapped_column(Float, default=121.4737)
    latitude: Mapped[float] = mapped_column(Float, default=31.2304)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    max_load: Mapped[int] = mapped_column(Integer, default=5)
    rating: Mapped[float] = mapped_column(Float, default=95.0)
    work_status: Mapped[str] = mapped_column(String(20), default="available", index=True)

    user: Mapped[User] = relationship(back_populates="worker_profile")
