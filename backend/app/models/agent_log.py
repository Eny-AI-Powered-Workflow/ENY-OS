# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/agent_log.py
"""
Agent logs model.
"""
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # success, error, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
