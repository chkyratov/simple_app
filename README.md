# One Window Simple

Упрощенная версия проекта One Window, реализованная на Flask и SQLAlchemy.

## Технологии
- Flask - веб-фреймворк
- SQLAlchemy - ORM для работы с базой данных
- Flask-Login - управление авторизацией
- SQLite - база данных

## Структура проекта
- `app.py` - основной файл приложения
- `models.py` - модели данных
- `routes.py` - маршруты приложения
- `templates/` - HTML шаблоны
- `static/` - статические файлы (CSS, JS)

## Установка и запуск
1. Создайте виртуальное окружение:
```bash
python -m venv venv
venv\Scripts\activate
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите приложение:
```bash
python app.py
```

4. Откройте браузер и перейдите по адресу http://localhost:5000
