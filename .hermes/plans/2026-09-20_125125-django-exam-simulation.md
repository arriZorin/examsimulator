# Django Multiple-Choice Exam Simulation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a secure Django web application where students register with biodata, take timed multiple-choice exams, submit answers, view results/evaluations, and review their result history, while staff can create exams and bulk-import questions from TXT, Markdown, DOCX, and PDF files.

**Architecture:** Use a server-rendered Django monolith with Django templates, class/function-based views, Django authentication, and SQLite. Split the project into `accounts` (student identity/profile), `exams` (question bank, exams, attempts, scoring), and `question_imports` (file extraction, parsing, validation, and import reports). The server is authoritative for timing and scoring; browser JavaScript only displays the countdown and submits when time expires.

**Tech Stack:** Python 3.11+, Django 5.2 LTS, SQLite, Django templates, Bootstrap 5 (or simple project CSS), vanilla JavaScript, `python-docx` for DOCX extraction, `PyMuPDF` for PDF extraction, `pytest`, `pytest-django`, and `factory-boy`.

---

## 1. Scope and assumptions

### Included in version 1

- Student registration using a unique username and password.
- Student biodata: full name, email, date of birth, gender (optional), phone number, school/institution, class/grade, and student ID (optional).
- Staff-managed question bank and exams through Django admin plus a dedicated bulk-import page.
- Questions with four or more answer options and exactly one correct option.
- Different exams can have different durations.
- One active attempt per student per exam.
- Server-enforced deadline, automatic submission after expiry, scoring, result summary, detailed evaluation, and dashboard history.
- Imports from `.txt`, `.md`, `.docx`, and text-based `.pdf` documents.
- Import preview and validation before database insertion.

### Explicit version 1 decisions

- Use single-answer multiple-choice questions, not “select all that apply.”
- Store questions and answer choices in normalized relational tables.
- Freeze each attempt’s question order and submitted answer data. Do not derive historical scores again from a mutable question bank.
- Use Django sessions and built-in authentication rather than a separate REST API or SPA.
- Treat PDF OCR as out of scope initially. Scanned/image-only PDFs should fail with a clear message explaining that extractable text is required.
- All exam deadlines use timezone-aware server timestamps.
- Evaluation becomes available after submission/expiry. A future setting can delay evaluation until an exam closes globally.

### Terminology

- **Exam:** A configured assessment with title, duration, publication state, and selected questions.
- **Attempt:** One student’s timed exam session.
- **Result:** The final score and summary for a submitted/expired attempt.
- **Evaluation:** A per-question review showing the student’s answer, correct answer, correctness, and explanation.

---

## 2. Proposed project structure

```text
examsim/
├── manage.py
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── accounts/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   ├── migrations/
│   └── tests/
├── exams/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── selectors.py
│   ├── services.py
│   ├── urls.py
│   ├── views.py
│   ├── migrations/
│   └── tests/
├── question_imports/
│   ├── admin.py
│   ├── apps.py
│   ├── extractors.py
│   ├── forms.py
│   ├── models.py
│   ├── parser.py
│   ├── services.py
│   ├── urls.py
│   ├── views.py
│   └── tests/
├── templates/
│   ├── base.html
│   ├── registration/
│   ├── accounts/
│   ├── exams/
│   └── question_imports/
├── static/
│   ├── css/app.css
│   └── js/exam_timer.js
└── tests/
    └── test_smoke.py
```

---

## 3. Data model

### `accounts.StudentProfile`

- `user`: one-to-one relation to `django.contrib.auth.models.User`.
- `full_name`: required.
- `date_of_birth`: optional unless the product owner makes it mandatory.
- `gender`: optional choice field.
- `phone_number`: optional.
- `institution`: optional.
- `grade_or_class`: optional.
- `student_id`: optional, indexed; make unique only if the organization guarantees uniqueness.
- `created_at`, `updated_at`.

Keep username, password hash, first/last name, and email in Django’s `User`; do not duplicate passwords or store plaintext credentials.

### `exams.Question`

- `text`: question prompt.
- `explanation`: optional feedback shown during evaluation.
- `is_active`: prevents future selection without deleting history.
- `created_by`: nullable staff user reference.
- `created_at`, `updated_at`.

### `exams.Option`

- `question`: foreign key to `Question`.
- `text`: option text.
- `is_correct`: boolean.
- `position`: positive integer for stable display order.
- Unique constraint on `(question, position)`.

Business validation must guarantee at least four options and exactly one correct option. Since a row-level SQLite check cannot count related rows, enforce this in forms/import services and test it explicitly.

### `exams.Exam`

- `title`, `description`, and optional instructions.
- `duration_minutes`: positive integer specific to this exam.
- `is_published`: controls student visibility.
- `available_from`, `available_until`: optional availability window.
- `max_attempts`: default 1.
- `show_evaluation`: default true.
- `created_by`, `created_at`, `updated_at`.

### `exams.ExamQuestion`

- `exam`: foreign key.
- `question`: foreign key.
- `position`: display order.
- `points`: positive decimal/integer, default 1.
- Unique constraints on `(exam, question)` and `(exam, position)`.

### `exams.Attempt`

- `exam`, `student`.
- `status`: `IN_PROGRESS`, `SUBMITTED`, or `EXPIRED`.
- `started_at`, `expires_at`, `submitted_at`.
- `score`, `maximum_score`, and `percentage` snapshots.
- `correct_count`, `incorrect_count`, `unanswered_count` snapshots.
- Database indexes on `(student, -started_at)` and `(exam, status)`.

`expires_at` must be calculated once at attempt creation as `started_at + exam.duration_minutes`; later changes to an exam duration must not alter an active attempt.

### `exams.AttemptQuestion`

- `attempt`, source `question`, `position`, and `points`.
- Snapshot fields: `question_text` and `explanation`.
- This freezes the questions included in the attempt and their order.

### `exams.AttemptOption`

- `attempt_question`, optional source `option`, `position`, `option_text`, and `is_correct_snapshot`.
- This preserves evaluation accuracy if staff later edits question-bank choices.

### `exams.Answer`

- `attempt_question` one-to-one.
- `selected_option`: nullable relation to `AttemptOption`.
- `answered_at`.
- `is_correct` snapshot assigned during finalization.

### `question_imports.ImportBatch`

- `uploaded_by`, original filename, file type, status, counts, error report, created timestamp.
- Optional stored source file only if audit/replay is required. Otherwise process and discard it to reduce retention risk.

---

## 4. Canonical bulk-import format

All four file types should be converted to plain text and then passed into one parser. This avoids implementing different question semantics per format.

Recommended format:

```text
QUESTION: What is the capital of France?
OPTION: Berlin
OPTION: Madrid
OPTION: Paris
OPTION: Rome
ANSWER: 3
EXPLANATION: Paris is the capital and largest city of France.
---
QUESTION: Which protocol secures HTTP traffic?
OPTION: FTP
OPTION: HTTPS
OPTION: SMTP
OPTION: Telnet
OPTION: SSH
ANSWER: 2
EXPLANATION: HTTPS is HTTP transported over TLS.
```

Rules:

- `QUESTION:` starts a question block.
- Every block requires at least four non-empty `OPTION:` lines; five or more are valid.
- `ANSWER:` is the 1-based option number and must identify exactly one option.
- `EXPLANATION:` is optional and may continue on indented lines.
- `---` separates blocks.
- Blank lines are allowed.
- `.txt` and `.md` are decoded as UTF-8 (support UTF-8 BOM).
- `.docx` paragraphs are extracted in document order with `python-docx`.
- `.pdf` page text is extracted in page order with PyMuPDF.
- Reject unsupported extensions, oversized files, encrypted PDFs, empty extraction output, malformed blocks, fewer than four options, duplicate option positions, and out-of-range answers.
- Preview must display valid records and line/block-specific errors. Nothing is saved until staff confirms the preview.
- Confirmation must execute inside `transaction.atomic()` to prevent partial imports.

---

## 5. Detailed implementation plan

### Task 1: Bootstrap the Django project and test tooling

**Objective:** Establish a reproducible Django project with a passing smoke test.

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `manage.py`
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: `tests/test_smoke.py`

**Steps:**

1. Define runtime dependencies: Django 5.2 LTS, `python-docx`, and `PyMuPDF`.
2. Define development dependencies: `pytest`, `pytest-django`, `factory-boy`, `coverage`, and `ruff`.
3. Configure SQLite at `BASE_DIR / "db.sqlite3"`, templates, static files, timezone support, authentication redirects, and safe upload limits.
4. Write a failing smoke test that calls Django’s system check and requests an initial route.
5. Run `python -m pytest tests/test_smoke.py -v`; expect failure before setup is complete.
6. Complete project wiring and run `python manage.py check` plus the smoke test; expect success.
7. Commit: `chore: bootstrap Django exam simulation project`.

### Task 2: Add base layout and public home page

**Objective:** Provide shared navigation, message rendering, responsive layout, and login-aware links.

**Files:**
- Create: `templates/base.html`
- Create: `templates/home.html`
- Create: `static/css/app.css`
- Modify: `config/urls.py`
- Test: `tests/test_smoke.py`

**Steps:**

1. Add tests for status 200, page title, anonymous login/register links, and authenticated dashboard/logout links.
2. Run tests and confirm failure.
3. Implement the base template and home route using semantic, keyboard-accessible HTML.
4. Run tests and `python manage.py check`.
5. Commit: `feat: add application shell and home page`.

### Task 3: Implement student profile data

**Objective:** Persist student biodata linked to Django authentication.

**Files:**
- Create: `accounts/models.py`
- Create: `accounts/admin.py`
- Create: `accounts/migrations/0001_initial.py`
- Test: `accounts/tests/test_models.py`

**Steps:**

1. Write tests for one profile per user, field lengths, string representation, and timestamps.
2. Run model tests and verify they fail.
3. Implement `StudentProfile`, model constraints, admin registration, and migration.
4. Run `python manage.py makemigrations --check`, `python manage.py migrate`, and model tests.
5. Commit: `feat: add student biodata profile`.

### Task 4: Implement registration, login, logout, and profile editing

**Objective:** Let students enter username, credentials, and biodata safely.

**Files:**
- Create: `accounts/forms.py`
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Create: `templates/registration/login.html`
- Create: `templates/accounts/register.html`
- Create: `templates/accounts/profile.html`
- Modify: `config/urls.py`
- Test: `accounts/tests/test_auth_views.py`

**Steps:**

1. Test successful registration, duplicate username, invalid/mismatched password, required biodata, transaction rollback, login, logout via POST, and authenticated profile editing.
2. Verify tests fail.
3. Build a registration form that creates `User` and `StudentProfile` inside `transaction.atomic()`.
4. Use Django password validators and CSRF protection; never log raw passwords.
5. Protect profile routes with `login_required` and enforce ownership.
6. Run auth tests.
7. Commit: `feat: add student registration and profile management`.

### Task 5: Implement question and option models

**Objective:** Create a reusable question bank supporting four or more options.

**Files:**
- Create: `exams/models.py`
- Create: `exams/migrations/0001_initial.py`
- Test: `exams/tests/test_question_models.py`

**Steps:**

1. Test question creation, stable option ordering, unique positions, four-option minimum validation, five-plus options, zero/multiple correct options, and inactive questions.
2. Verify failure.
3. Implement `Question` and `Option` plus a domain validation method/service that inspects the complete option set.
4. Ensure import and admin paths call the same validator; avoid duplicating rules.
5. Run migrations and model tests.
6. Commit: `feat: add validated multiple-choice question bank`.

### Task 6: Add question administration with inline options

**Objective:** Let staff create and edit valid questions in Django admin.

**Files:**
- Create: `exams/admin.py`
- Create/modify: `exams/forms.py`
- Test: `exams/tests/test_admin.py`

**Steps:**

1. Test that non-staff users cannot access admin.
2. Test admin formset rejection for fewer than four options and anything other than one correct option.
3. Add `OptionInline`, question list filters/search, and formset-wide validation.
4. Confirm an admin can save a question with four and with six options.
5. Run admin tests.
6. Commit: `feat: add validated question administration`.

### Task 7: Implement exams and exam-question assignment

**Objective:** Configure independently timed exams and ordered question membership.

**Files:**
- Modify: `exams/models.py`
- Create: `exams/migrations/0002_exam_examquestion.py`
- Modify: `exams/admin.py`
- Test: `exams/tests/test_exam_models.py`

**Steps:**

1. Test positive duration, optional availability window validation, unique question/order constraints, publication state, point values, and maximum attempts.
2. Verify tests fail.
3. Implement `Exam` and `ExamQuestion`.
4. Add admin editing with ordered question assignment.
5. Verify an unpublished exam and an exam outside its availability window are not available to students.
6. Run tests and commit: `feat: add timed exam configuration`.

### Task 8: Implement attempt snapshots and state transitions

**Objective:** Start an exam safely and freeze its timing/content for the student.

**Files:**
- Modify: `exams/models.py`
- Create: `exams/migrations/0003_attempt_snapshots.py`
- Create: `exams/services.py`
- Test: `exams/tests/test_attempt_service.py`

**Steps:**

1. Test `start_attempt()` for unpublished/unavailable exams, empty exams, attempt limits, active-attempt reuse, and exact deadline calculation.
2. Test that attempt question/option snapshots preserve positions, points, correct options, prompt text, and explanations.
3. Test concurrent starts conceptually through a transaction and uniqueness constraint so duplicate active attempts cannot be created.
4. Implement creation within `transaction.atomic()` and use database constraints where SQLite supports them.
5. Verify editing a source question after the start does not mutate the attempt snapshot.
6. Run tests and commit: `feat: create immutable timed exam attempts`.

### Task 9: Build exam catalog and start confirmation

**Objective:** Show students available exams and start/resume them intentionally.

**Files:**
- Create: `exams/selectors.py`
- Create: `exams/views.py`
- Create: `exams/urls.py`
- Create: `templates/exams/exam_list.html`
- Create: `templates/exams/exam_detail.html`
- Modify: `config/urls.py`
- Test: `exams/tests/test_exam_catalog_views.py`

**Steps:**

1. Test login requirements and filtering by publication/availability.
2. Test detail display of duration and question count without exposing answers.
3. Require POST plus CSRF to start an attempt; GET must not create data.
4. Resume an existing active attempt instead of resetting its timer.
5. Run tests and commit: `feat: add exam catalog and attempt start flow`.

### Task 10: Implement answering and server-authoritative timing

**Objective:** Render an active attempt, save answers, and prevent work after the deadline.

**Files:**
- Modify: `exams/views.py`
- Modify: `exams/forms.py`
- Create: `templates/exams/take_exam.html`
- Create: `static/js/exam_timer.js`
- Test: `exams/tests/test_take_exam_views.py`

**Steps:**

1. Test attempt ownership, valid snapshot-option selection, answer replacement, unanswered questions, CSRF, and prevention of cross-question option IDs.
2. Test requests one second before, at, and after `expires_at` using a controllable clock/mocking.
3. Implement either one-page answer submission or an autosave POST endpoint. Prefer explicit per-change autosave with visible “saved” state, while retaining all answers in a final form fallback.
4. Pass only the authoritative ISO deadline to JavaScript. Display the countdown, warning state, and automatic POST submit at zero.
5. Every answer/save/submit endpoint must check server time; never trust the browser timer or a client-supplied remaining-time value.
6. Avoid sending `is_correct` or correct option identifiers in HTML/JSON while an attempt is active.
7. Run view and timing tests.
8. Commit: `feat: add timed exam answering experience`.

### Task 11: Implement finalization and scoring

**Objective:** Finalize attempts idempotently and persist a score snapshot.

**Files:**
- Modify: `exams/services.py`
- Modify: `exams/views.py`
- Test: `exams/tests/test_scoring.py`

**Steps:**

1. Test correct, incorrect, and unanswered counting; weighted points; zero-question protection; percentage rounding; manual submission; expiration; and repeated submissions.
2. Verify failure.
3. Implement `finalize_attempt(attempt, reason)` inside `transaction.atomic()` with row locking where supported.
4. Calculate from attempt snapshots, set each answer’s `is_correct`, and persist total score, maximum score, percentage, counts, timestamp, and final status.
5. Make repeated finalization return the same stored result without double work or changing timestamps.
6. Ensure a late submit finalizes as expired but still scores answers saved before the deadline.
7. Run tests and commit: `feat: finalize and score exam attempts`.

### Task 12: Build result and evaluation pages

**Objective:** Show a result summary and an optional detailed evaluation after the exam.

**Files:**
- Modify: `exams/views.py`
- Create: `templates/exams/result.html`
- Create: `templates/exams/evaluation.html`
- Test: `exams/tests/test_result_views.py`

**Steps:**

1. Test result ownership, finalized-only access, score/count display, and evaluation-button visibility.
2. Test evaluation content for correct, incorrect, and unanswered items, including explanation and the selected/correct option indicators.
3. Test that no evaluation is exposed when `show_evaluation=False`.
4. Implement a result page with an **Evaluate Answers** button at the end of the exam.
5. Make evaluation accessible and visually distinguish states without relying only on color.
6. Run tests and commit: `feat: add exam results and detailed evaluation`.

### Task 13: Build the student dashboard and history

**Objective:** Give each student a private history of exam results and active attempts.

**Files:**
- Create: `templates/accounts/dashboard.html`
- Modify: `accounts/views.py`
- Modify: `accounts/urls.py`
- Modify: `exams/selectors.py`
- Test: `accounts/tests/test_dashboard.py`

**Steps:**

1. Test login requirement and strict user scoping.
2. Test history ordering, exam title, attempt date, status, score, percentage, result link, evaluation link, empty state, and resume link for a still-active attempt.
3. Add pagination to avoid loading an unbounded attempt history.
4. Avoid N+1 queries with `select_related`/`prefetch_related`; assert a reasonable query count.
5. Run dashboard tests and commit: `feat: add student result history dashboard`.

### Task 14: Implement normalized question parser

**Objective:** Parse the canonical text format into validated, database-independent records.

**Files:**
- Create: `question_imports/parser.py`
- Test: `question_imports/tests/test_parser.py`
- Create fixtures: `question_imports/tests/fixtures/questions.txt`

**Steps:**

1. Write unit tests for four options, more than four options, optional/multiline explanation, blank lines, multiple blocks, UTF-8 text, malformed labels, absent answer, nonnumeric/out-of-range answer, and fewer than four options.
2. Represent parser output with typed dataclasses such as `ParsedQuestion` and structured `ParseError` values containing block/line context.
3. Keep parsing pure: no database access and no partial mutation.
4. Run parser tests and commit: `feat: parse normalized bulk question format`.

### Task 15: Implement TXT, Markdown, DOCX, and PDF extraction

**Objective:** Convert each supported upload to normalized plain text safely.

**Files:**
- Create: `question_imports/extractors.py`
- Add fixtures: `question_imports/tests/fixtures/questions.md`
- Add fixtures: `question_imports/tests/fixtures/questions.docx`
- Add fixtures: `question_imports/tests/fixtures/questions.pdf`
- Test: `question_imports/tests/test_extractors.py`

**Steps:**

1. Test extension and MIME/content checks, UTF-8/BOM handling, DOCX paragraph order, PDF page order, encrypted PDF rejection, scanned/empty PDF rejection, corrupt files, and maximum file size.
2. Verify failures.
3. Implement a dispatcher using a strict extension allowlist and per-format extractor.
4. Normalize newlines but preserve enough line structure for useful parser errors.
5. Never execute macros or embedded content; `python-docx` should only read paragraph text.
6. Run extractor tests and commit: `feat: extract questions from supported documents`.

### Task 16: Implement import preview and atomic confirmation

**Objective:** Let staff validate uploads before creating question-bank records.

**Files:**
- Create: `question_imports/models.py`
- Create: `question_imports/forms.py`
- Create: `question_imports/services.py`
- Create: `question_imports/views.py`
- Create: `question_imports/urls.py`
- Create: `templates/question_imports/upload.html`
- Create: `templates/question_imports/preview.html`
- Create: `templates/question_imports/report.html`
- Modify: `config/urls.py`
- Test: `question_imports/tests/test_import_views.py`
- Test: `question_imports/tests/test_import_service.py`

**Steps:**

1. Test staff-only access, upload validation, preview rendering, invalid-record reporting, tamper-resistant confirmation, atomic rollback, and successful counts.
2. Do not trust serialized question content returned by a hidden browser field. Store a short-lived server-side preview payload in the session/cache or reparse a controlled temporary upload on confirmation.
3. On confirmation, create every `Question` and its options within one transaction and call the same domain validator used by admin.
4. Record `ImportBatch` status and counts, without storing sensitive raw data unnecessarily.
5. Add a duplicate warning based on normalized question text; initially warn rather than silently discard.
6. Run import tests and commit: `feat: add previewed atomic bulk question import`.

### Task 17: Add expiry reconciliation

**Objective:** Ensure abandoned attempts become finalized even if the student closes the browser.

**Files:**
- Create: `exams/management/commands/finalize_expired_attempts.py`
- Test: `exams/tests/test_finalize_expired_command.py`

**Steps:**

1. Test that the command finalizes only overdue `IN_PROGRESS` attempts and is safe to run repeatedly.
2. Implement a management command that processes bounded batches.
3. Also lazily finalize expired attempts when dashboard/result/attempt routes encounter them, so correctness does not depend on a scheduler in development.
4. Document production scheduling (for example, once per minute via cron/task runner) without introducing Celery for version 1.
5. Run command tests and commit: `feat: reconcile abandoned expired attempts`.

### Task 18: Security, accessibility, and performance hardening

**Objective:** Close authorization, upload, timing, and usability gaps before release.

**Files:**
- Modify: `config/settings.py`
- Modify: relevant forms, views, templates, and tests
- Create: `exams/tests/test_security.py`
- Create: `question_imports/tests/test_upload_security.py`

**Steps:**

1. Add object-level authorization tests for attempts, results, evaluations, and imports.
2. Verify all mutating actions require POST and CSRF.
3. Add login throttling guidance or integrate a small proven package only if required for deployment.
4. Configure secure production settings through environment variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, HTTPS redirect, secure cookies, HSTS, and trusted origins.
5. Add upload size limits and helpful errors.
6. Add indexes and inspect expensive result/dashboard queries.
7. Check keyboard navigation, labels, focus states, timer announcements, contrast, and mobile layouts.
8. Run the complete suite and commit: `chore: harden exam application`.

### Task 19: Add end-to-end workflow coverage

**Objective:** Prove the core student and staff journeys work together.

**Files:**
- Create: `tests/test_exam_workflow.py`
- Create: `tests/test_import_workflow.py`

**Steps:**

1. Test staff imports a document, confirms valid questions, creates/publishes an exam, and assigns imported questions.
2. Test student registration with biodata, exam start, answer save, submission, result, evaluation, and dashboard history.
3. Test a second exam with a different timer to prove timing is exam-specific.
4. Test auto-expiry and an abandoned-attempt reconciliation path.
5. Run `python -m pytest -v` and coverage.
6. Commit: `test: cover complete exam simulation workflows`.

### Task 20: Documentation and release readiness

**Objective:** Make local setup, content authoring, testing, and deployment understandable.

**Files:**
- Create/modify: `README.md`
- Create: `docs/question-import-format.md`
- Create: `docs/deployment.md`

**Steps:**

1. Document Python setup, dependency installation, migrations, superuser creation, development server, and tests.
2. Document the exact canonical import format with valid and invalid examples.
3. Explain that scanned PDFs require OCR before upload.
4. Document exam creation, publication, timer semantics, result/evaluation behavior, backup/restore, and expiry-command scheduling.
5. Run final quality gates and manually execute the acceptance checklist below.
6. Commit: `docs: add setup administration and import guides`.

---

## 6. Key URLs

```text
/                              Home
/accounts/register/            Student registration
/accounts/login/               Login
/accounts/logout/              Logout (POST)
/accounts/profile/             Student biodata editor
/dashboard/                    Student active attempts and result history
/exams/                        Published/available exam list
/exams/<id>/                   Exam details and start confirmation
/exams/<id>/start/             Start/resume action (POST)
/attempts/<id>/                Timed answering screen
/attempts/<id>/answer/         Save answer (POST)
/attempts/<id>/submit/         Final submission (POST)
/attempts/<id>/result/         Result summary
/attempts/<id>/evaluation/     Per-question evaluation
/question-imports/upload/      Staff upload
/question-imports/<id>/preview/ Staff preview
/question-imports/<id>/confirm/ Staff confirmation (POST)
/admin/                        Staff administration
```

---

## 7. Test and validation strategy

### Automated checks

Run in this order:

```bash
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python -m ruff check .
python -m pytest -v
python -m coverage run -m pytest
python -m coverage report --fail-under=90
```

Important test classes:

- Model constraints and domain validation.
- Permission and ownership boundaries.
- Timer boundary conditions and timezone-aware deadlines.
- Idempotent scoring/finalization.
- Snapshot immutability after source question edits.
- Four-option minimum and support for five or more options.
- Parser/extractor behavior for each file format.
- Malformed, corrupt, oversized, encrypted, and empty files.
- Transaction rollback during import.
- Student dashboard query behavior and privacy.

### Manual acceptance checklist

1. Create a staff user and student user.
2. Register a student with username, password, and biodata.
3. Import one TXT, one MD, one DOCX, and one text-based PDF file.
4. Confirm preview catches a question with only three options.
5. Confirm a valid question with six options imports successfully.
6. Create Exam A with 10 minutes and Exam B with 30 minutes.
7. Verify each attempt receives the correct fixed deadline.
8. Answer some questions, refresh, and verify saved answers remain selected.
9. Attempt to modify the countdown in browser tools and verify the server still rejects late answers.
10. Submit and verify score, correct/incorrect/unanswered counts, and percentage.
11. Select **Evaluate Answers** and verify each answer and explanation.
12. Open the dashboard and verify the result appears in history.
13. Log in as another student and verify the first student’s attempt/result is inaccessible.
14. Close an active exam, wait until expiry, run expiry reconciliation, and verify the attempt is finalized.

---

## 8. Risks and mitigations

- **Browser timer manipulation:** Use server timestamps for all authorization and submission decisions; JavaScript is display-only.
- **Question edits corrupt history:** Snapshot prompt, choices, correctness, explanation, order, and points when an attempt begins.
- **Partial/invalid bulk imports:** Parse before writing, preview errors, and confirm inside one atomic transaction.
- **DOCX/PDF extraction differences:** Normalize all extracted content into one canonical parser and maintain real fixture files.
- **Scanned PDFs:** Detect empty/near-empty extraction and return a clear OCR-required error; do not pretend the import succeeded.
- **At-least-four-options rule:** It spans related rows, so enforce it in shared domain validation used by admin and imports rather than relying only on a database constraint.
- **Abandoned attempts:** Use lazy finalization plus a repeatable management command.
- **SQLite write contention:** Appropriate for a small deployment/prototype; document PostgreSQL migration as the scale-up path if simultaneous exam traffic grows.
- **Correct answers leaking:** Render only attempt option identifiers/text during active exams, and expose correctness only after finalization when evaluation is enabled.
- **Concurrent final submission:** Make finalization transactional and idempotent.

---

## 9. Open product questions

These do not block the initial architecture, but should be confirmed before polishing UI/business rules:

1. Which biodata fields are mandatory beyond username and full name?
2. Is student self-registration allowed, or should staff create/import student accounts?
3. Can students attempt an exam more than once, and which result should appear as primary?
4. Should evaluation appear immediately, or only after a global exam closing date?
5. Are negative marks, partial credit, randomized questions, or randomized options required?
6. Should staff be able to import questions directly into a selected exam, or only into the question bank?
7. Must image-based questions or images embedded in DOCX/PDF be supported?
8. Does “season exam” mean an individual exam session, an academic term/semester, or an exam sitting shared by a cohort?

Version 1 can proceed with the defaults documented in Section 1 and evolve these settings later without changing the core attempt snapshot design.
