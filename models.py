from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    task_num = Column(Integer, index=True)
    micro_tag = Column(String, index=True)
    text = Column(Text)
    correct_answer = Column(String)
    explanation = Column(Text)

class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    question_id = Column(String, index=True)  # <-- ИСПРАВЛЕНО НА СТРОКУ
    is_correct = Column(Boolean)
    time_spent = Column(Integer)
    timestamp = Column(String)