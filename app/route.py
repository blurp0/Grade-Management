from flask_login import current_user, login_required, login_user, logout_user
from flask import Blueprint, abort, request, redirect, url_for, render_template, flash, session
from sqlalchemy import distinct, func
from .model import Grade, GradeStatus, Instructor, Subject, User, Student
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

    subject_ids = [subject.id for subject in instructor.subjects]

    # Query for graded students count
    graded_student_count = (
        db.session.query(func.count(distinct(Grade.student_id)))
        .filter(
            Grade.subject_id.in_(subject_ids),
            Grade.status == GradeStatus.GRADED
        )
        .scalar()
    )

    # Query for incomplete students count
    incomplete_student_count = (
        db.session.query(func.count(distinct(Grade.student_id)))
        .filter(
            Grade.subject_id.in_(subject_ids),
            Grade.status == GradeStatus.INCOMPLETE
        )
        .scalar()
    )

    return render_template(
        "instructor/home.html",
        instructor=instructor,
        graded_student_count=graded_student_count,
        incomplete_student_count=incomplete_student_count,
    )


@bp.route("/instructor/students")
@login_required
def instructor_students():
    if current_user.role != "instructor":
        abort(403)

    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    subjects = Subject.query.filter_by(instructor_id=instructor.id).all()

    subject_students = {
        subject: Student.query.filter_by(subject_id=subject.id).all()
        for subject in subjects
    }

    return render_template("instructor/student.html", subject_students=subject_students)


@bp.route("/assign-grade", methods=["POST"])
def assign_grade():
    student_id = request.form["student_id"]
    subject_id = request.form["subject_id"]
    grade_input = request.form["grade"].strip()

    # Determine status based on grade input
    if not grade_input:
        status = GradeStatus.INCOMPLETE
    elif grade_input == "5.0":
        status = GradeStatus.FAILED
    else:
        try:
            grade_val = float(grade_input)
            if 1.0 <= grade_val < 5.0:
                status = GradeStatus.GRADED
            else:
                status = GradeStatus.FAILED
        except ValueError:
            flash("Invalid grade format. Use numbers like 1.0 - 5.0.", "danger")
            return redirect(url_for("main.instructor_students"))

    # Get or create Grade record
    grade = Grade.query.filter_by(student_id=student_id, subject_id=subject_id).first()
    if not grade:
        grade = Grade(student_id=student_id, subject_id=subject_id)

    grade.grade = grade_input  # Store the raw input (can be "5.0", "3.0", etc.)
    grade.status = status

    db.session.add(grade)
    db.session.commit()

    flash("Grade saved successfully!", "success")
    return redirect(url_for("main.instructor_students"))

@bp.route("/instructor/profile", methods=["GET", "POST"])
@login_required
def instructor_profile():
    if current_user.role != "instructor":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    instructor = current_user.instructor
    if not instructor:
        instructor = Instructor(user_id=current_user.id, name="")
        db.session.add(instructor)
        db.session.commit()

    all_subjects = Subject.query.all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        selected_subject_ids = request.form.getlist("subject_ids")  # note: name="subject_ids" in form

        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("main.instructor_profile"))

        instructor.name = name

        for subject in all_subjects:
            if str(subject.id) in selected_subject_ids:
                subject.instructor_id = instructor.id
            else:
                if subject.instructor_id == instructor.id:
                    subject.instructor_id = None

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.instructor_profile"))

    return render_template("instructor/profile.html", instructor=instructor, all_subjects=all_subjects)





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
