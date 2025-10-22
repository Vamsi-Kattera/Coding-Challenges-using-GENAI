import json
import random

with open("questions.json", "r") as f:
    QUESTION_BANK = json.load(f)

LEVELS = ["easy", "medium", "hard"]

def get_question(level):
    questions = QUESTION_BANK.get(level, [])
    return random.choice(questions) if questions else None

def adjust_level(score_history):
    if not score_history:
        return "easy"

    recent = score_history[-3:]
    accuracy = sum(recent) / len(recent)

    if accuracy >= 0.8:
        return "hard"
    elif accuracy >= 0.5:
        return "medium"
    else:
        return "easy"

def get_quiz_question():
    quiz_questions = QUESTION_BANK.get("quiz", [])
    return random.choice(quiz_questions) if quiz_questions else None
