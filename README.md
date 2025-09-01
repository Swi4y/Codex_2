# Разговорный дневник

Локальный CLI и веб‑приложение для ведения небольших дневниковых записей с автоматическим отражением и вопросом.

## Примеры
```bash
ally init
ally write "Сегодня я переживаю из-за дедлайна" --dialog=sentiment
ally write "Классно поработал над проектом, есть прогресс" --dialog=rules
ally list --limit 5
ally pulse
ally export --fmt html --out journal.html
ALLY_DATA_PATH=./mydata ally web
```

## Установка
```bash
pip install -e .
```

## Запуск тестов
```bash
pytest
```
