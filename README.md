# Medicare – Local Clinic Management System

Django-based web application for managing clinic users, patients, doctors, appointments and medical records.

## Technology
- Python 3.13
- Django 6.1
- HTML/CSS
- Django ORM
- PostgreSQL on Render
- Gunicorn
- WhiteNoise

## Local setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Render deployment

The repository includes `render.yaml` for a Render web service and PostgreSQL database.

Set:
- `ALLOWED_HOSTS` to the Render hostname
- `CSRF_TRUSTED_ORIGINS` to `https://<your-render-hostname>`

Do not commit `.env`, `db.sqlite3`, `venv/`, or production secrets.
