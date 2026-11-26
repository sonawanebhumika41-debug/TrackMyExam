from datetime import datetime
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(50))
    nationality = db.Column(db.String(100))
    category = db.Column(db.String(100))
    qualification = db.Column(db.String(255))
    preparation_level = db.Column(db.String(100))
    selected_exams = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    exam_name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)
    exam_date = db.Column(db.Date)
    status = db.Column(db.String(30), default='Active', nullable=False)
    eligibility_rules = db.relationship('EligibilityRule', backref='exam', cascade='all, delete-orphan')
    question_papers = db.relationship('QuestionPaper', backref='exam', cascade='all, delete-orphan')
    syllabus_items = db.relationship('SyllabusItem', backref='exam', cascade='all, delete-orphan')

class EligibilityRule(db.Model):
    __tablename__ = 'eligibility_rules'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    minimum_age = db.Column(db.Integer)
    maximum_age = db.Column(db.Integer)
    qualification = db.Column(db.String(255))
    nationality = db.Column(db.String(100))
    category = db.Column(db.String(100))
    other_requirements = db.Column(db.Text)

class QuestionPaper(db.Model):
    __tablename__ = 'question_papers'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(150))
    paper_type = db.Column(db.String(100), default='Previous Year Paper')
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='question_paper', cascade='all, delete-orphan')

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_paper_id = db.Column(db.Integer, db.ForeignKey('question_papers.id'), nullable=False)
    subject = db.Column(db.String(150))
    topic = db.Column(db.String(255))
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(30), default='Medium')

class MockTest(db.Model):
    __tablename__ = 'mock_tests'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    prompt = db.Column(db.Text)
    selected_years = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='mock_tests')
    exam = db.relationship('Exam')
    questions = db.relationship('MockTestQuestion', backref='mock_test', cascade='all, delete-orphan')

class MockTestQuestion(db.Model):
    __tablename__ = 'mock_test_questions'
    id = db.Column(db.Integer, primary_key=True)
    mock_test_id = db.Column(db.Integer, db.ForeignKey('mock_tests.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question = db.relationship('Question')

class TestResult(db.Model):
    __tablename__ = 'test_results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    mock_test_id = db.Column(db.Integer, db.ForeignKey('mock_tests.id'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    wrong_answers = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='results')
    mock_test = db.relationship('MockTest', backref=db.backref('result', uselist=False))

class StudyPlan(db.Model):
    __tablename__ = 'study_plans'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(150))
    study_date = db.Column(db.Date)
    status = db.Column(db.String(30), default='Pending')
    student = db.relationship('Student', backref='study_plans')

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = db.relationship('Student', backref='notes')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='notifications')

class SyllabusItem(db.Model):
    __tablename__ = 'syllabus_items'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default='Not Started')

def create_default_admin():
    import os
    if Admin.query.first():
        return
    admin = Admin(name=os.getenv('ADMIN_NAME', 'TrackMyExam Admin'), email=os.getenv('ADMIN_EMAIL', 'admin@trackmyexam.com'))
    admin.set_password(os.getenv('ADMIN_PASSWORD', 'change-this-password'))
    db.session.add(admin)
    db.session.commit()
