import enum
from datetime import datetime
from . import db

# User table for both students and instructors
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # login username
    password_hash = db.Column(db.String(128), nullable=False)          # hashed password
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'instructor'

    # Relationships (optional)
    student = db.relationship("Student", uselist=False, back_populates="user")
    instructor = db.relationship("Instructor", uselist=False, back_populates="user")


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    year_and_section = db.Column(db.String(50))
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"))

    user = db.relationship("User", back_populates="student")
    subject = db.relationship("Subject", back_populates="students")
    grades = db.relationship("Grade", back_populates="student")


class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

    user = db.relationship("User", back_populates="instructor")
    subjects = db.relationship("Subject", back_populates="instructor")


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    instructor_id = db.Column(db.Integer, db.ForeignKey("instructor.id"))
    instructor = db.relationship("Instructor", back_populates="subjects")

    students = db.relationship("Student", back_populates="subject")
    grades = db.relationship("Grade", back_populates="subject")

class GradeStatus(enum.Enum):
    GRADED = "graded"
    INCOMPLETE = "incomplete"
    FAILED = "failed"

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer,
                           db.ForeignKey("student.id"),
                           nullable=False)
    subject_id = db.Column(db.Integer,
                           db.ForeignKey("subject.id"),
                           nullable=False)

    grade = db.Column(db.String(10))                     # e.g. 95, “A‑”
    status = db.Column(db.Enum(GradeStatus),             # graded / incomplete / failed
                       default=GradeStatus.GRADED,
                       nullable=False)

    updated_at = db.Column(                              # NEW COLUMN
        db.DateTime,
        default=datetime.utcnow,        # set on INSERT
        onupdate=datetime.utcnow,       # refresh on UPDATE
        nullable=False,
    )

    # relationships
    student = db.relationship("Student", back_populates="grades")
    subject = db.relationship("Subject", back_populates="grades")
    
