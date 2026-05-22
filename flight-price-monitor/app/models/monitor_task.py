from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MonitorTask(Base):
    __tablename__ = "monitor_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(20), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(20), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    time_start: Mapped[str] = mapped_column(String(8), nullable=False)
    time_end: Mapped[str] = mapped_column(String(8), nullable=False)
    max_price: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
