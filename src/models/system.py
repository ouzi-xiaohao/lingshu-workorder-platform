from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class SystemConfig(TimestampMixin, Base):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(String(300), default="")
    value_type: Mapped[str] = mapped_column(String(20), default="string")
