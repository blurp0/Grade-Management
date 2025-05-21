import enum
from datetime import datetime
from . import db
from app import login_manager
from flask_login import UserMixin

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'instructor'

    student = db.relationship("Student", uselist=False, back_populates="user")
    instructor = db.relationship("Instructor", uselist=False, back_populates="user")
    
    def set_password(self, pwd):
        self.password = pwd

    def check_password(self, pwd):
        return self.password == pwd 


# Association table for many-to-many relationship between students and subjects
student_subject = db.Table(
    "student_subject",
    db.Column("student_id", db.Integer, db.ForeignKey("student.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id"), primary_key=True),
)


instructor_subject = db.Table(
    "instructor_subject",
    db.Column("instructor_id", db.Integer, db.ForeignKey("instructor.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id"), primary_key=True),
)



class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    student_no = db.Column(db.String(50), unique=True, nullable=True)  # new student number column
    name = db.Column(db.String(120), nullable=False)
    year_and_section = db.Column(db.String(50))

    user = db.relationship("User", back_populates="student")
    subjects = db.relationship("Subject", secondary=student_subject, back_populates="students")
    grades = db.relationship("Grade", back_populates="student")



class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

    user = db.relationship("User", back_populates="instructor")
    subjects = db.relationship(
        "Subject",
        secondary=instructor_subject,
        back_populates="instructors"
    )


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    instructors = db.relationship(
        "Instructor",
        secondary=instructor_subject,
        back_populates="subjects"
    )
    students = db.relationship(
        "Student",
        secondary=student_subject,
        back_populates="subjects"
    )
    grades = db.relationship("Grade", back_populates="subject")



class GradeStatus(enum.Enum):
    GRADED = "graded"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)

    midterm = db.Column(db.Integer)
    finals = db.Column(db.Integer)

    total_quiz_score = db.Column(db.Float, default=0.0)
    total_assignment_score = db.Column(db.Float, default=0.0)

    # ✅ NEW: Item count columns
    quiz_items = db.Column(db.Integer, default=0)
    assignment_items = db.Column(db.Integer, default=0)
    midterm_items = db.Column(db.Integer, default=0)
    final_items = db.Column(db.Integer, default=0)

    grade = db.Column(db.String(10))
    status = db.Column(db.Enum(GradeStatus), default=GradeStatus.GRADED, nullable=False)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    student = db.relationship("Student", back_populates="grades")
    subject = db.relationship("Subject", back_populates="grades")

    __table_args__ = (
        db.UniqueConstraint("student_id", "subject_id", name="_student_subject_uc"),
    )



class GradingWeight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    
    quiz_weight = db.Column(db.Float, nullable=False)
    assignment_weight = db.Column(db.Float, nullable=False)
    midterm_weight = db.Column(db.Float, nullable=False)
    final_weight = db.Column(db.Float, nullable=False)

    # Relationships (optional)
    instructor = db.relationship('Instructor', backref='grading_weights')
    subject = db.relationship('Subject', backref='grading_weights')

    __table_args__ = (
        db.UniqueConstraint('instructor_id', 'subject_id', name='unique_weight_per_subject'),
    )
