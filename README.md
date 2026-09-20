# Exam Simulation

A Django 5.2 / SQLite web application for timed multiple-choice exams.

## Features

- Student accounts and biodata profiles
- Questions with any number of options (minimum four, exactly one correct)
- Published exams with availability windows, attempt limits, and dedicated timers
- Server-enforced expiration, immutable question snapshots, scoring, results, and evaluation
- Student dashboard with paginated result history
- Staff-only bulk import from TXT, Markdown, DOCX, and text-based PDF
- Import preview and atomic confirmation

## Run locally

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/. Use `/admin/` to create an exam and add imported or manually created questions. A ready-to-import example is in `sample_questions.txt`.

## Import format

```text
QUESTION: Question text
OPTION: First choice
OPTION: Second choice
OPTION: Third choice
OPTION: Fourth choice
ANSWER: 2
EXPLANATION: Optional feedback
---
```

`ANSWER` is the one-based option number. Each question requires at least four options. DOCX and PDF files must contain the same markers; scanned PDFs are not OCRed.

## Tests and checks

```bash
uv run pytest
uv run ruff check .
uv run python manage.py check --deploy
```

For periodic cleanup, run `uv run python manage.py finalize_expired_attempts` from a scheduler. The dashboard and result pages also enforce expiration on access.

## Production notes

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_TIME_ZONE`. Serve behind HTTPS, configure secure cookies/HSTS at deployment, and replace SQLite for high-concurrency deployments.
