from sqlalchemy import Column, Integer, Text, DateTime, String
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass

class ThreadLog(Base):
    __tablename__ = "thread_logs"
    id = Column(Integer, primary_key=True)
    thread_id = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    user_name = Column(Text, nullable=False)
    thread_name = Column(Text, nullable=False)
    channel_id = Column(Integer, nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow)
