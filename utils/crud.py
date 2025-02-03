from sqlalchemy import select
from datetime import datetime
from sqlalchemy.orm import Session

from .models import ThreadLog
from utils.db_alchemy import engine

def init_db():
    ThreadLog.metadata.create_all(engine)

def log_thread_closure(user_id: int, thread_id: int, channel_id: int):
    """
    Логирует закрытие ветки в базе данных
    """
    with Session(bind=engine) as session:
        stmt = select(ThreadLog).where(ThreadLog.thread_id == thread_id)
        existing_log = session.scalars(stmt).first()

        if existing_log:
            return None

        log = ThreadLog(
            user_id=user_id,
            thread_id=thread_id,
            channel_id=channel_id,
            closed_at=datetime.utcnow(),
        )
        session.add(log)
        session.commit()
        return log

def get_thread_logs(user_id: int = None, channel_id: int = None):
    """
    Получает логи закрытых веток из базы данных с фильтрацией
    """
    with Session(bind=engine) as session:
        stmt = select(ThreadLog)
        if user_id:
            stmt = stmt.where(ThreadLog.user_id == user_id)
        if channel_id:
            stmt = stmt.where(ThreadLog.channel_id == channel_id)

        return session.scalars(stmt).all()

def was_thread_closed(thread_id: int):
    """
    Проверяет, была ли ветка ранее закрыта
    """
    with Session(bind=engine) as session:
        stmt = select(ThreadLog).where(ThreadLog.thread_id == thread_id)
        return session.scalars(stmt).first() is not None
