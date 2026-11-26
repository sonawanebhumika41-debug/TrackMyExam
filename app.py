from datetime import datetime, date
from functools import wraps
import csv, io, os, random, re, uuid
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
from config import Config
from models import db, Admin, Student, Exam, EligibilityRule, QuestionPaper, Question, MockTest, MockTestQuestion, TestResult, StudyPlan, Note, Notification, SyllabusItem, create_default_admin
app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)
with app.app_context():
    db.create_all()
    create_default_admin()
ALLOWED_UPLOADS = {'pdf', 'csv', 'txt'}

def admin_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login as administrator first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def student_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'student_id' not in session:
            flash('Please login as student first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def current_student():
    return Student.query.get_or_404(session['student_id'])

def selected_exam_names(student):
    return [x.strip() for x in (student.selected_exams or '').split(',') if x.strip()]

def selected_exams(student):
    names = selected_exam_names(student)
    return Exam.query.filter(Exam.exam_name.in_(names)).all() if names else []

def age_on_date(dob, on_date=None):
    if not dob:
        return None
    on_date = on_date or date.today()
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOADS

def prompt_tokens(prompt):
    return {x for x in re.findall('[a-zA-Z]{3,}', (prompt or '').lower()) if x not in {'the', 'and', 'for', 'from', 'with', 'give', 'make', 'create', 'questions', 'question', 'test', 'exam', 'generate', 'medium', 'easy', 'hard', 'level', 'year', 'years', 'last'}}

def choose_questions(exam_id, years, subject, prompt, count):
    q = Question.query.filter_by(exam_id=exam_id)
    if years:
        q = q.join(QuestionPaper).filter(QuestionPaper.year.in_(years))
    if subject:
        q = q.filter(Question.subject.ilike(f'%{subject}%'))
    pool = q.all()
    tokens = prompt_tokens(prompt)
    if tokens:

        def relevance(item):
            text = ' '.join([item.question_text or '', item.subject or '', item.topic or '', item.explanation or '']).lower()
            return sum((1 for t in tokens if t in text))
        pool.sort(key=relevance, reverse=True)
        relevant = [x for x in pool if relevance(x) > 0]
        if relevant:
            pool = relevant + [x for x in pool if x not in relevant]
    random.shuffle(pool)
    return pool[:max(1, min(count, 50))]

@app.route('/')
def splash():
    return render_template('auth/splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kind = request.form.get('login_type', 'student')
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if kind == 'admin':
            obj = Admin.query.filter_by(email=email).first()
            if obj and check_password_hash(obj.password_hash, password):
                session.clear()
                session['admin_id'] = obj.id
                session['admin_name'] = obj.name
                return redirect(url_for('admin_dashboard'))
            flash('Invalid admin email or password.', 'danger')
        else:
            obj = Student.query.filter_by(email=email).first()
            if obj and check_password_hash(obj.password_hash, password):
                session.clear()
                session['student_id'] = obj.id
                session['student_name'] = obj.full_name
                return redirect(url_for('dashboard'))
            flash('Invalid student email or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    exams = Exam.query.filter_by(status='Active').order_by(Exam.exam_name).all()
    if request.method == 'POST':
        data = {k: request.form.get(k, '').strip() for k in ['full_name', 'email', 'gender', 'nationality', 'category', 'qualification', 'preparation_level']}
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not data['full_name'] or not data['email'] or (not password):
            flash('Name, email and password are required.', 'danger')
            return render_template('auth/register.html', exams=exams)
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', exams=exams)
        if Student.query.filter_by(email=data['email']).first() or Admin.query.filter_by(email=data['email']).first():
            flash('This email is already registered.', 'warning')
            return render_template('auth/register.html', exams=exams)
        dob = None
        if request.form.get('dob'):
            try:
                dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                return render_template('auth/register.html', exams=exams)
        s = Student(**data, dob=dob, selected_exams=', '.join(request.form.getlist('exams')))
        s.set_password(password)
        db.session.add(s)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html', exams=exams)

@app.route('/dashboard')
@student_required
def dashboard():
    student = current_student()
    exams = selected_exams(student)
    results = TestResult.query.filter_by(student_id=student.id).order_by(TestResult.submitted_at.desc()).all()
    return render_template('student/dashboard.html', student=student, exams=exams, results=results[:5])

@app.route('/profile')
@student_required
def profile():
    return render_template('student/student-profile.html', student=current_student())

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/my-exams')
@student_required
def my_exams():
    return render_template('student/my_exams.html', student=current_student(), exams=selected_exams(current_student()))

@app.route('/eligibility')
@student_required
def eligibility():
    student = current_student()
    rows = []
    today = date.today()
    age = age_on_date(student.dob, today)
    for exam in selected_exams(student):
        rules = EligibilityRule.query.filter_by(exam_id=exam.id).all()
        status = 'Requirements not available'
        reasons = []
        if rules:
            status = 'Eligible'
            for r in rules:
                if r.minimum_age is not None and (age is None or age < r.minimum_age):
                    status = 'Not Eligible'
                    reasons.append(f'Minimum age: {r.minimum_age}')
                if r.maximum_age is not None and (age is None or age > r.maximum_age):
                    status = 'Not Eligible'
                    reasons.append(f'Maximum age: {r.maximum_age}')
                if r.qualification and student.qualification and (r.qualification.lower() not in student.qualification.lower()):
                    status = 'Not Eligible'
                    reasons.append(f'Qualification: {r.qualification}')
                if r.nationality and student.nationality and (r.nationality.lower() != student.nationality.lower()):
                    status = 'Not Eligible'
                    reasons.append(f'Nationality: {r.nationality}')
                if r.category and student.category and (r.category.lower() != student.category.lower()):
                    status = 'Not Eligible'
                    reasons.append(f'Category: {r.category}')
        rows.append((exam, status, reasons))
    return render_template('student/eligibility.html', student=student, rows=rows)

@app.route('/syllabus')
@student_required
def syllabus():
    return render_template('student/syllabus.html', student=current_student(), items=SyllabusItem.query.filter(SyllabusItem.exam_id.in_([e.id for e in selected_exams(current_student())])).all())

@app.route('/subjects')
@student_required
def subjects():
    items = SyllabusItem.query.filter(SyllabusItem.exam_id.in_([e.id for e in selected_exams(current_student())])).all()
    return render_template('student/subjects.html', student=current_student(), items=items)

@app.route('/mock-tests', methods=['GET', 'POST'])
@student_required
def mock_tests():
    student = current_student()
    exams = selected_exams(student)
    if request.method == 'POST':
        try:
            exam_id = int(request.form.get('exam_id'))
            years = [int(y) for y in request.form.getlist('years')]
            subject = request.form.get('subject', '').strip()
            prompt = request.form.get('prompt', '').strip()
            count = int(request.form.get('count', '10'))
        except (ValueError, TypeError):
            flash('Please enter valid mock-test settings.', 'danger')
            return redirect(url_for('mock_tests'))
        exam = Exam.query.get_or_404(exam_id)
        if exam not in exams:
            flash('You can only create tests for your selected exams.', 'danger')
            return redirect(url_for('mock_tests'))
        questions = choose_questions(exam_id, years, subject, prompt, count)
        if not questions:
            flash('No questions are available for this exam/year selection. Ask Admin to add/import questions.', 'warning')
            return redirect(url_for('mock_tests'))
        test = MockTest(student_id=student.id, exam_id=exam.id, prompt=prompt, selected_years=', '.join(map(str, years)) or 'All available years')
        db.session.add(test)
        db.session.flush()
        for q in questions:
            db.session.add(MockTestQuestion(mock_test_id=test.id, question_id=q.id))
        db.session.commit()
        return redirect(url_for('take_mock_test', mock_test_id=test.id))
    paper_years = {e.id: [p.year for p in QuestionPaper.query.filter_by(exam_id=e.id).order_by(QuestionPaper.year.desc()).all()] for e in exams}
    return render_template('student/mock_tests.html', student=student, exams=exams, paper_years=paper_years)

@app.route('/mock-tests/<int:mock_test_id>', methods=['GET', 'POST'])
@student_required
def take_mock_test(mock_test_id):
    test = MockTest.query.get_or_404(mock_test_id)
    if test.student_id != session['student_id']:
        return redirect(url_for('mock_tests'))
    questions = [x.question for x in test.questions]
    if request.method == 'POST':
        correct = 0
        for q in questions:
            if request.form.get(f'q_{q.id}', '').upper() == q.correct_answer.upper():
                correct += 1
        total = len(questions)
        wrong = total - correct
        pct = correct / total * 100 if total else 0
        result = TestResult(student_id=session['student_id'], mock_test_id=test.id, total_questions=total, correct_answers=correct, wrong_answers=wrong, score=correct, percentage=pct)
        db.session.add(result)
        db.session.commit()
        return redirect(url_for('result_detail', result_id=result.id))
    return render_template('student/take_mock_test.html', student=current_student(), test=test, questions=questions)

@app.route('/results')
@student_required
def results():
    return render_template('student/results.html', student=current_student(), results=TestResult.query.filter_by(student_id=session['student_id']).order_by(TestResult.submitted_at.desc()).all())

@app.route('/results/<int:result_id>')
@student_required
def result_detail(result_id):
    r = TestResult.query.get_or_404(result_id)
    if r.student_id != session['student_id']:
        return redirect(url_for('results'))
    return render_template('student/result_detail.html', student=current_student(), result=r)

@app.route('/study-planner', methods=['GET', 'POST'])
@student_required
def study_planner():
    if request.method == 'POST':
        d = None
        if request.form.get('study_date'):
            try:
                d = datetime.strptime(request.form['study_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        if request.form.get('task', '').strip():
            db.session.add(StudyPlan(student_id=session['student_id'], task=request.form['task'].strip(), subject=request.form.get('subject', '').strip(), study_date=d))
            db.session.commit()
            flash('Study task added.', 'success')
        return redirect(url_for('study_planner'))
    plans = StudyPlan.query.filter_by(student_id=session['student_id']).order_by(StudyPlan.study_date.asc()).all()
    return render_template('student/study_planner.html', student=current_student(), plans=plans)

@app.route('/study-planner/delete/<int:plan_id>')
@student_required
def delete_plan(plan_id):
    p = StudyPlan.query.get_or_404(plan_id)
    if p.student_id == session['student_id']:
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('study_planner'))

@app.route('/notes', methods=['GET', 'POST'])
@student_required
def notes():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if title and content:
            db.session.add(Note(student_id=session['student_id'], title=title, content=content))
            db.session.commit()
            flash('Note saved.', 'success')
        return redirect(url_for('notes'))
    return render_template('student/notes.html', student=current_student(), notes=Note.query.filter_by(student_id=session['student_id']).order_by(Note.updated_at.desc()).all())

@app.route('/notes/delete/<int:note_id>')
@student_required
def delete_note(note_id):
    n = Note.query.get_or_404(note_id)
    if n.student_id == session['student_id']:
        db.session.delete(n)
        db.session.commit()
    return redirect(url_for('notes'))

@app.route('/documents')
@student_required
def documents():
    return render_template('student/documents.html', student=current_student())

@app.route('/notifications')
@student_required
def notifications():
    ns = Notification.query.filter((Notification.student_id == session['student_id']) | Notification.student_id.is_(None)).order_by(Notification.created_at.desc()).all()
    return render_template('student/notifications.html', student=current_student(), notifications=ns)

@app.route('/settings')
@student_required
def settings():
    return render_template('student/settings.html', student=current_student())

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Admin logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html', admin_name=session.get('admin_name'), exam_count=Exam.query.count(), student_count=Student.query.count(), paper_count=QuestionPaper.query.count(), question_count=Question.query.count())

@app.route('/admin/exams', methods=['GET', 'POST'])
@admin_required
def manage_exams():
    if request.method == 'POST':
        name = request.form.get('exam_name', '').strip()
        if name and (not Exam.query.filter_by(exam_name=name).first()):
            d = None
            if request.form.get('exam_date'):
                try:
                    d = datetime.strptime(request.form['exam_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            db.session.add(Exam(exam_name=name, description=request.form.get('description', '').strip(), exam_date=d, status=request.form.get('status', 'Active')))
            db.session.commit()
            flash('Exam added.', 'success')
        else:
            flash('Exam name is empty or already exists.', 'warning')
        return redirect(url_for('manage_exams'))
    return render_template('admin/manage_exams.html', exams=Exam.query.order_by(Exam.exam_name).all())

@app.route('/admin/exams/edit/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def edit_exam(exam_id):
    e = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        e.exam_name = request.form.get('exam_name', '').strip()
        e.description = request.form.get('description', '').strip()
        e.status = request.form.get('status', 'Active')
        if request.form.get('exam_date'):
            try:
                e.exam_date = datetime.strptime(request.form['exam_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        db.session.commit()
        flash('Exam updated.', 'success')
        return redirect(url_for('manage_exams'))
    return render_template('admin/edit_exam.html', exam=e)

@app.route('/admin/exams/delete/<int:exam_id>')
@admin_required
def delete_exam(exam_id):
    e = Exam.query.get_or_404(exam_id)
    db.session.delete(e)
    db.session.commit()
    flash('Exam deleted.', 'success')
    return redirect(url_for('manage_exams'))

@app.route('/admin/exam-date', methods=['GET', 'POST'])
@admin_required
def exam_date():
    if request.method == 'POST':
        e = Exam.query.get_or_404(int(request.form['exam_id']))
        e.exam_date = datetime.strptime(request.form['exam_date'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Exam date updated.', 'success')
        return redirect(url_for('exam_date'))
    return render_template('admin/exam_date.html', exams=Exam.query.order_by(Exam.exam_name).all())

@app.route('/admin/eligibility', methods=['GET', 'POST'])
@admin_required
def eligibility_rules():
    exams = Exam.query.order_by(Exam.exam_name).all()
    if request.method == 'POST':
        r = EligibilityRule(exam_id=int(request.form['exam_id']), minimum_age=int(request.form['minimum_age']) if request.form.get('minimum_age') else None, maximum_age=int(request.form['maximum_age']) if request.form.get('maximum_age') else None, qualification=request.form.get('qualification', '').strip(), nationality=request.form.get('nationality', '').strip(), category=request.form.get('category', '').strip(), other_requirements=request.form.get('other_requirements', '').strip())
        db.session.add(r)
        db.session.commit()
        flash('Eligibility rule added.', 'success')
        return redirect(url_for('eligibility_rules'))
    return render_template('admin/eligibility_rules.html', exams=exams, rules=EligibilityRule.query.order_by(EligibilityRule.id.desc()).all())

@app.route('/admin/eligibility/edit/<int:rule_id>', methods=['GET', 'POST'])
@admin_required
def edit_eligibility(rule_id):
    r = EligibilityRule.query.get_or_404(rule_id)
    if request.method == 'POST':
        r.exam_id = int(request.form['exam_id'])
        r.minimum_age = int(request.form['minimum_age']) if request.form.get('minimum_age') else None
        r.maximum_age = int(request.form['maximum_age']) if request.form.get('maximum_age') else None
        r.qualification = request.form.get('qualification', '').strip()
        r.nationality = request.form.get('nationality', '').strip()
        r.category = request.form.get('category', '').strip()
        r.other_requirements = request.form.get('other_requirements', '').strip()
        db.session.commit()
        flash('Rule updated.', 'success')
        return redirect(url_for('eligibility_rules'))
    return render_template('admin/edit_eligibility.html', rule=r, exams=Exam.query.all())

@app.route('/admin/eligibility/delete/<int:rule_id>')
@admin_required
def delete_eligibility(rule_id):
    r = EligibilityRule.query.get_or_404(rule_id)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for('eligibility_rules'))

@app.route('/admin/question-papers', methods=['GET', 'POST'])
@admin_required
def question_papers():
    exams = Exam.query.order_by(Exam.exam_name).all()
    if request.method == 'POST':
        try:
            exam_id = int(request.form['exam_id'])
            year = int(request.form['year'])
        except (ValueError, TypeError):
            flash('Exam and year are required.', 'danger')
            return redirect(url_for('question_papers'))
        title = request.form.get('title', '').strip() or f'{year} Previous Year Paper'
        f = request.files.get('paper_file')
        saved_name = None
        path = None
        if f and f.filename:
            if not allowed_file(f.filename):
                flash('Allowed files: PDF, CSV, TXT.', 'danger')
                return redirect(url_for('question_papers'))
            saved_name = f'{uuid.uuid4().hex}_{secure_filename(f.filename)}'
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_name))
            path = saved_name
        p = QuestionPaper(exam_id=exam_id, year=year, title=title, subject=request.form.get('subject', '').strip(), paper_type=request.form.get('paper_type', 'Previous Year Paper'), file_name=f.filename if f and f.filename else None, file_path=path)
        db.session.add(p)
        db.session.commit()
        if f and f.filename and f.filename.lower().endswith('.csv'):
            import_questions_from_csv(p, os.path.join(app.config['UPLOAD_FOLDER'], saved_name), exam_id)
        flash('Question paper added. If CSV was uploaded, its questions were imported.', 'success')
        return redirect(url_for('question_papers'))
    papers = QuestionPaper.query.order_by(QuestionPaper.year.desc()).all()
    return render_template('admin/question_papers.html', exams=exams, papers=papers)

def import_questions_from_csv(paper, path, exam_id):
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                required = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
                if not all((row.get(k) for k in required)):
                    continue
                db.session.add(Question(exam_id=exam_id, question_paper_id=paper.id, subject=row.get('subject') or paper.subject, topic=row.get('topic', ''), question_text=row['question_text'], option_a=row['option_a'], option_b=row['option_b'], option_c=row['option_c'], option_d=row['option_d'], correct_answer=row['correct_answer'].strip().upper()[:1], explanation=row.get('explanation', ''), difficulty=row.get('difficulty', 'Medium')))
        db.session.commit()
    except Exception:
        db.session.rollback()

@app.route('/admin/question-papers/delete/<int:paper_id>')
@admin_required
def delete_question_paper(paper_id):
    p = QuestionPaper.query.get_or_404(paper_id)
    db.session.delete(p)
    db.session.commit()
    flash('Question paper deleted.', 'success')
    return redirect(url_for('question_papers'))

@app.route('/admin/questions', methods=['GET', 'POST'])
@admin_required
def manage_questions():
    papers = QuestionPaper.query.order_by(QuestionPaper.year.desc()).all()
    if request.method == 'POST':
        pid = int(request.form['question_paper_id'])
        p = QuestionPaper.query.get_or_404(pid)
        correct = request.form.get('correct_answer', '').upper()
        if correct not in {'A', 'B', 'C', 'D'}:
            flash('Correct answer must be A, B, C or D.', 'danger')
            return redirect(url_for('manage_questions'))
        db.session.add(Question(exam_id=p.exam_id, question_paper_id=pid, subject=request.form.get('subject', '').strip() or p.subject, topic=request.form.get('topic', '').strip(), question_text=request.form.get('question_text', '').strip(), option_a=request.form.get('option_a', '').strip(), option_b=request.form.get('option_b', '').strip(), option_c=request.form.get('option_c', '').strip(), option_d=request.form.get('option_d', '').strip(), correct_answer=correct, explanation=request.form.get('explanation', '').strip(), difficulty=request.form.get('difficulty', 'Medium')))
        db.session.commit()
        flash('Question added.', 'success')
        return redirect(url_for('manage_questions'))
    return render_template('admin/questions.html', papers=papers, questions=Question.query.order_by(Question.id.desc()).all())

@app.route('/admin/questions/delete/<int:question_id>')
@admin_required
def delete_question(question_id):
    q = Question.query.get_or_404(question_id)
    db.session.delete(q)
    db.session.commit()
    return redirect(url_for('manage_questions'))

@app.route('/admin/syllabus', methods=['GET', 'POST'])
@admin_required
def admin_syllabus():
    exams = Exam.query.all()
    if request.method == 'POST':
        db.session.add(SyllabusItem(exam_id=int(request.form['exam_id']), subject=request.form['subject'].strip(), topic=request.form['topic'].strip()))
        db.session.commit()
        return redirect(url_for('admin_syllabus'))
    return render_template('admin/syllabus.html', exams=exams, items=SyllabusItem.query.order_by(SyllabusItem.id.desc()).all())

@app.route('/admin/uploads/<path:filename>')
@admin_required
def admin_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
if __name__ == '__main__':
    import webbrowser, threading
    threading.Timer(1.2, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(debug=True, use_reloader=False)
