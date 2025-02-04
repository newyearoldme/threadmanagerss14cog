from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import DateTime, BigInteger


class Base(DeclarativeBase):
    pass


class ThreadLog(Base):
    __tablename__ = "thread_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
