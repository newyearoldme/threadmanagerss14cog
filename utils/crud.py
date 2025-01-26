from utils.db_alchemy import get_db
from utils.models import ThreadLog
from datetime import datetime

def log_thread_closure(user_id: int, user_name: str, thread_id: int, thread_name: str, channel_id: int):
    """
    Логирует закрытие ветки в базе данных
    """
    with get_db() as session:
        existing_log = session.query(ThreadLog).filter_by(thread_id=thread_id).first()
        if existing_log:
            return None

        log = ThreadLog(
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_id,
            thread_name=thread_name,
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
    with get_db() as session:
        query = session.query(ThreadLog)
        if user_id:
            query = query.filter(ThreadLog.user_id == user_id)
        if channel_id:
            query = query.filter(ThreadLog.channel_id == channel_id)
        return query.all()

def was_thread_closed(thread_id: int):
    """
    Проверяет, была ли ветка ранее закрыта
    """
    with get_db() as session:
        return session.query(ThreadLog).filter_by(thread_id=thread_id).first() is not None
