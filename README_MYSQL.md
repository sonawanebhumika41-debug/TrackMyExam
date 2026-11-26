# TrackMyExam — MySQL Setup

1. Create the database:

```sql
CREATE DATABASE IF NOT EXISTS trackmyexam;
```

2. Set DB_USER, DB_PASSWORD, DB_HOST, DB_PORT and DB_NAME in `.env`.
3. Activate the virtual environment.
4. Install requirements: `pip install -r requirements.txt`
5. Run: `python app.py`

The application calls `db.create_all()` on startup, so all SQLAlchemy tables are created automatically. Existing tables are not dropped.

## PYQ workflow

Admin → Question Papers / PYQ → select exam/year → upload the actual PDF/CSV/TXT.

For automatic question import, use CSV with these headers:

`question_text,option_a,option_b,option_c,option_d,correct_answer,subject,topic,explanation,difficulty`

The student Mock Tests page then uses the stored exam/year/question data and the student's prompt to select relevant questions. It does not invent real PYQs.
