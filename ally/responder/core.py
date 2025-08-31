from typing import List

STYLES = {
    "gentle": {
        "question": "Что для тебя сейчас важно?",
        "step": "Сделай маленький вдох и запиши ещё мысль позже.",
    },
    "skeptic": {
        "question": "Почему это значимо?",
        "step": "Попробуй посмотреть на ситуацию иначе.",
    },
    "poet": {
        "question": "Как это звучит в твоей душе?",
        "step": "Найди метафору и сохрани её.",
    },
}


def respond(threads: List[str], style: str = "gentle") -> str:
    s = STYLES.get(style, STYLES["gentle"])
    threads_part = ", ".join(threads)
    parts = [f"нити: {threads_part}", f"вопрос: {s['question']}"]
    if step := s.get("step"):
        parts.append(f"маленький шаг: {step}")
    return "\n\n".join(parts)
