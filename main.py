from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import models, database
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SubmitAttempt(BaseModel):
    session_id: int
    question_id: str
    is_correct: bool
    time_spent: int

class FinishSession(BaseModel):
    session_id: int
    total_time_seconds: int

@app.get("/generate_full_test")
def generate_full_test(db: Session = Depends(get_db)):
    new_session = models.TestSession(total_questions=26)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    test_questions = []

    # 1. Задания 1-21
    for i in range(1, 22):
        q = db.query(models.Question).filter(models.Question.task_num == i).order_by(func.random()).first()
        if q:
            test_questions.append({
                "id": str(q.id),
                "task_num": q.task_num,
                "type": "standard",
                "text": q.text,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "tag": q.tag
            })

    # 2. Макротекст (22-26)
    macro_text = db.query(models.MacroText).order_by(func.random()).first()
    
    if macro_text:
        text_data = {
            "text_id": macro_text.id,
            "author": macro_text.author,
            "source_info": macro_text.source_info,
            "sentences": json.loads(macro_text.sentences_json)
        }

        macro_qs = db.query(models.MacroQuestion).filter(models.MacroQuestion.text_id == macro_text.id).order_by(models.MacroQuestion.task_num).all()
        for mq in macro_qs:
            parsed_correct = json.loads(mq.correct_answer) if mq.q_type == 'review_gap_fill' else mq.correct_answer
            
            test_questions.append({
                "id": mq.id,
                "task_num": mq.task_num,
                "type": mq.q_type,
                "instruction": mq.instruction,
                "options": json.loads(mq.options_json) if mq.options_json else [],
                "correct_answer": parsed_correct,
                "explanation": mq.explanation,
                "highlight_sentences": json.loads(mq.highlight_sentences_json) if mq.highlight_sentences_json else [],
                "review_text": mq.review_text,
                "terms_list": json.loads(mq.terms_list_json) if mq.terms_list_json else [],
                "macro_text": text_data
            })

    return {
        "session_id": new_session.id,
        "questions": test_questions
    }

@app.post("/submit_attempt")
def submit_attempt(attempt: SubmitAttempt, db: Session = Depends(get_db)):
    new_attempt = models.Attempt(
        session_id=attempt.session_id,
        question_id=attempt.question_id,
        is_correct=attempt.is_correct,
        time_spent=attempt.time_spent
    )
    db.add(new_attempt)
    db.commit()
    return {"status": "success"}

@app.post("/finish_session")
def finish_session(data: FinishSession, db: Session = Depends(get_db)):
    session = db.query(models.TestSession).filter(models.TestSession.id == data.session_id).first()
    if session:
        session.is_finished = True
        session.time_spent_seconds = data.total_time_seconds
        
        correct_count = db.query(models.Attempt).filter(
            models.Attempt.session_id == data.session_id,
            models.Attempt.is_correct == True
        ).count()
        session.score = correct_count
        
        db.commit()
        return {"status": "success", "score": correct_count}
    raise HTTPException(status_code=404, detail="Сессия не найдена")

@app.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    # Завершенные сессии
    finished_sessions = db.query(models.TestSession).filter(models.TestSession.is_finished == True).all()
    completed_sessions_count = len(finished_sessions)
    
    total_session_time = sum(s.time_spent_seconds for s in finished_sessions if s.time_spent_seconds)
    avg_session_time = round(total_session_time / completed_sessions_count) if completed_sessions_count > 0 else 0

    # История последних 10 вариантов
    recent_sessions_data = []
    for s in sorted(finished_sessions, key=lambda x: x.id, reverse=True)[:10]:
        acc = round((s.score / s.total_questions) * 100) if s.total_questions > 0 else 0
        recent_sessions_data.append({
            "id": s.id,
            "date": s.start_time.strftime("%d.%m %H:%M") if s.start_time else "—",
            "score": s.score,
            "total": s.total_questions,
            "accuracy": acc,
            "time_spent": s.time_spent_seconds if s.time_spent_seconds else 0
        })

    # Общая статистика по ответам
    total_attempts = db.query(models.Attempt).count()
    correct_attempts_count = db.query(models.Attempt).filter(models.Attempt.is_correct == True).count()
    accuracy = round((correct_attempts_count / total_attempts) * 100) if total_attempts > 0 else 0

    # Динамика по дням
    by_date_query = db.query(
        func.date(models.Attempt.timestamp).label("date"),
        func.count(models.Attempt.id).label("total"),
        func.sum(func.cast(models.Attempt.is_correct, models.Integer)).label("correct"),
        func.sum(models.Attempt.time_spent).label("time")
    ).group_by("date").all()

    by_date = {}
    for row in by_date_query:
        by_date[str(row.date)] = {
            "total": row.total,
            "correct": row.correct if row.correct else 0,
            "time": row.time if row.time else 0
        }

    # Поиск ошибок по темам (Слепые пятна)
    error_attempts = db.query(models.Attempt).filter(models.Attempt.is_correct == False).all()
    tag_errors = {}
    for a in error_attempts:
        if a.question_id and a.question_id.isdigit():
            q = db.query(models.Question).filter(models.Question.id == int(a.question_id)).first()
            tag_name = q.tag if (q and q.tag) else f"Задание {q.task_num if q else '?'}"
        elif a.question_id and a.question_id.startswith("macro"):
            tag_name = "Работа с текстом (22-26)"
        else:
            tag_name = "Разное"
        
        tag_errors[tag_name] = tag_errors.get(tag_name, 0) + 1

    top_errors = []
    for tag, count in sorted(tag_errors.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_errors.append({"tag": tag, "errors": count})

    return {
        "total_variants": completed_sessions_count,
        "total_answered": total_attempts,
        "accuracy": accuracy,
        "avg_session_time": avg_session_time,
        "recent_sessions": recent_sessions_data,
        "by_date": by_date,
        "top_errors": top_errors
    }