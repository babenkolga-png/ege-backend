from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    task_num = Column(Integer, index=True)
    text = Column(String)
    correct_answer = Column(String)
    explanation = Column(String)
    tag = Column(String)

# НОВОЕ: Таблица для хранения сессий (прохождений вариантов)
class TestSession(Base):
    __tablename__ = "test_sessions"
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, default=0)
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=26)
    is_finished = Column(Boolean, default=False)

# ОБНОВЛЕНО: Таблица попыток теперь привязывается к сессии
class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=True) 
    question_id = Column(String, index=True) # String, чтобы хранить '15' и 'macro_text_001'
    is_correct = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    time_spent = Column(Integer)

# НОВОЕ: Таблица для Макротекстов
class MacroText(Base):
    __tablename__ = "macro_texts"
    id = Column(String, primary_key=True, index=True) 
    author = Column(String)
    source_info = Column(String)
    sentences_json = Column(Text) # Храним массив предложений в виде текста

# НОВОЕ: Таблица для заданий 22-26
class MacroQuestion(Base):
    __tablename__ = "macro_questions"
    id = Column(String, primary_key=True, index=True)
    text_id = Column(String, ForeignKey("macro_texts.id"))
    task_num = Column(Integer)
    q_type = Column(String)
    instruction = Column(Text)
    options_json = Column(Text, nullable=True)
    correct_answer = Column(Text)
    explanation = Column(Text)
    highlight_sentences_json = Column(Text)
    review_text = Column(Text, nullable=True)
    terms_list_json = Column(Text, nullable=True)