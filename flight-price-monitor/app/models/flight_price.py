from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FlightPrice(Base):
    __tablename__ = "flight_prices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("monitor_tasks.id"))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    flight_no: Mapped[str] = mapped_column(String(30), nullable=False)
    airline: Mapped[str] = mapped_column(String(50), nullable=False)
    depart_airport: Mapped[str] = mapped_column(String(50), nullable=False)
    arrive_airport: Mapped[str] = mapped_column(String(50), nullable=False)
    depart_time: Mapped[str] = mapped_column(String(8), nullable=False)
    arrive_time: Mapped[str] = mapped_column(String(8), nullable=False)
    adult_price: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
