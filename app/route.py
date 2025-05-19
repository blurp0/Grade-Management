from flask_login import current_user, login_required, login_user, logout_user
from flask import Blueprint, request, redirect, url_for, render_template, flash, session
from .model import Instructor, Subject, User, Student
from . import db

bp = Blueprint("main", __name__)

@bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("main.home"))
    return render_template("base.html")

@bp.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return render_template("base.html")



# Instructor Navigation

@bp.route("/instructor")
def instructor():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        return "Instructor profile not found", 404
    
    subjects = instructor.subjects
    students_set = set()
    for subject in subjects:
        students_set.update(subject.students)
    students = list(students_set)
    
    return render_template("instructor/home.html", instructor=instructor, subjects=subjects, students=students)


@bp.route("/instructor/students")
def instructor_students():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        return "Instructor profile not found", 404

    subjects = instructor.subjects
    students_set = set()
    for subject in subjects:
        students_set.update(subject.students)
    students = list(students_set)

    return render_template("instructor/student.html", instructor=instructor, subjects=subjects, students=students)


@bp.route("/instructor/subjects")
def instructor_subjects():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        return "Instructor profile not found", 404

    subjects = instructor.subjects
    students_set = set()
    for subject in subjects:
        students_set.update(subject.students)
    students = list(students_set)

    return render_template("instructor/subjects.html", instructor=instructor, subjects=subjects, students=students)

@bp.route("/instructor_profile")
def instructor_profile():
    return render_template("instructor/home.html")




# Student Navigation

@bp.route("/student")
def student():

    student = Student.query.filter_by(user_id=current_user.id).first()
    return render_template("student/home.html", student=student)

@bp.route("/student/profile", methods=["GET", "POST"])
def student_profile():
    # Assuming current_user is available and linked to a User
    student = current_user.student

    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        # Get form data
        student.name = request.form.get("name", student.name).strip()
        student.year_and_section = request.form.get("year_and_section", student.year_and_section).strip()

        # Update subject if provided
        subject_id = request.form.get("subject_id")
        if subject_id:
            student.subject_id = int(subject_id)
        else:
            student.subject_id = None

        # Save changes
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.student_profile"))

    # GET request: render profile form
    subjects = Subject.query.all()  # to list available subjects in dropdown

    return render_template("student/profile.html", student=student, subjects=subjects)


# Auth (Login/Register)

# ────────── REGISTER ──────────
@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        role     = request.form["role"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("main.register"))

        new_user = User(username=username, role=role)
        new_user.set_password(password)          # now stores plain text
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("auth/register.html")


# ────────── LOGIN ──────────
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password", "danger")
            return render_template("auth/login.html"), 401

        login_user(user)
        flash("Login successful!", "success")

        if user.role == "student":
            return redirect(url_for("main.student"))
        else:  # instructor
            return redirect(url_for("main.instructor"))

    return render_template("auth/login.html")

# ────────── LOGOUT ──────────
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.login"))
