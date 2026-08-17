from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import datetime
import random
from database import SessionLocal, engine 
import models

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AttemptCreate(BaseModel):
    question_id: str 
    is_correct: bool
    time_spent: int 

@app.get("/")
def read_root():
    return {"message": "Сервер ЕГЭ-2027 работает!"}

@app.get("/questions")
def get_questions(db: Session = Depends(get_db)):
    return db.query(models.Question).all()

@app.get("/generate_full_test")
def generate_full_test(db: Session = Depends(get_db)):
    incorrect_attempts = db.query(models.Attempt).filter(
        models.Attempt.user_id == 1, 
        models.Attempt.is_correct == False
    ).all()
    
    error_tags = {}
    for attempt in incorrect_attempts:
        # Игнорируем макротекст при сборке варианта 1-21
        if not attempt.question_id.startswith("macro_"):
            try:
                q_id = int(attempt.question_id)
                q = db.query(models.Question).filter(models.Question.id == q_id).first()
                if q:
                    error_tags[q.micro_tag] = error_tags.get(q.micro_tag, 0) + 1
            except ValueError:
                pass

    full_test = []
    available_task_nums = db.query(models.Question.task_num).distinct().all()
    task_nums = [t[0] for t in available_task_nums] 
    
    for task_i in task_nums:
        available_questions = db.query(models.Question).filter(models.Question.task_num == task_i).all()
        error_questions = [q for q in available_questions if q.micro_tag in error_tags]
        
        if error_questions:
            max_errors = max([error_tags[q.micro_tag] for q in error_questions])
            top_questions = [q for q in error_questions if error_tags[q.micro_tag] == max_errors]
            selected_q = random.choice(top_questions)
        else:
            selected_q = random.choice(available_questions)
            
        full_test.append(selected_q)
        
    full_test.sort(key=lambda x: x.task_num)
    return full_test

@app.post("/submit_attempt")
def submit_attempt(attempt: AttemptCreate, db: Session = Depends(get_db)):
    new_attempt = models.Attempt(
        user_id=1,
        question_id=attempt.question_id,
        is_correct=attempt.is_correct,
        time_spent=attempt.time_spent,
        timestamp=datetime.datetime.utcnow().isoformat()
    )
    db.add(new_attempt)
    db.commit()
    return {"status": "success"}

@app.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    all_attempts = db.query(models.Attempt).filter(models.Attempt.user_id == 1).all()
    
    total = len(all_attempts)
    correct = sum(1 for a in all_attempts if a.is_correct)
    percent = round((correct / total * 100), 1) if total > 0 else 0
    
    stats_by_date = {}
    error_tags = {}

    for attempt in all_attempts:
        date = attempt.timestamp[:10] 
        if date not in stats_by_date:
            stats_by_date[date] = {"total": 0, "correct": 0, "time": 0} 
            
        stats_by_date[date]["total"] += 1
        stats_by_date[date]["time"] += (attempt.time_spent or 0)
        
        if not attempt.is_correct:
            if attempt.question_id.startswith("macro_"):
                task_num = attempt.question_id.replace("macro_", "")
                tag = f"Задание {task_num} (Макротекст)"
                error_tags[tag] = error_tags.get(tag, 0) + 1
            else:
                try:
                    q_id = int(attempt.question_id)
                    q = db.query(models.Question).filter(models.Question.id == q_id).first()
                    tag = q.micro_tag if q else f"Неизвестный тег"
                    error_tags[tag] = error_tags.get(tag, 0) + 1
                except ValueError:
                    pass

    top_errors = sorted([{"tag": k, "errors": v} for k, v in error_tags.items()], key=lambda x: x["errors"], reverse=True)

    return {
        "total_answered": total, 
        "correct_answers": correct, 
        "accuracy": percent,
        "by_date": stats_by_date,
        "top_errors": top_errors
    }