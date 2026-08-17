import csv
from database import SessionLocal
from models import Question

def load_questions():
    db = SessionLocal()
    with open("questions.csv", mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            existing_question = db.query(Question).filter(Question.text == row['text']).first()
            if not existing_question:
                new_q = Question(
                    task_num=int(row['task_num']),
                    micro_tag=row['micro_tag'],
                    text=row['text'],
                    correct_answer=row['correct_answer'],
                    explanation=row['explanation']
                )
                db.add(new_q)
        db.commit()
        print("Новые вопросы из CSV успешно добавлены в базу данных!")
    db.close()

if __name__ == "__main__":
    load_questions()