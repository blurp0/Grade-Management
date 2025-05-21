from flask_login import current_user, login_required, login_user, logout_user
from flask import Blueprint, abort, jsonify, request, redirect, url_for, render_template, flash, session
import pandas as pd
from sqlalchemy import distinct, func
from .model import  Grade, GradeStatus, GradingWeight, Instructor, Subject, User, Student , student_subject
from . import db

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("main.home"))
    return render_template("base.html")

# Instructor Navigation


@bp.route("/instructor")
@login_required
def instructor():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        return "Instructor profile not found", 404

    subject_ids = [subject.id for subject in (instructor.subjects or [])]

    if not subject_ids:
        # No subjects yet, counts are zero
        graded_student_count = 0
        incomplete_student_count = 0
    else:
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
    if not instructor:
        flash("Instructor profile not found.", "danger")
        return redirect(url_for("main.home"))

    subjects = instructor.subjects
    subject_students = {}

    def calculate_numeric_grade(score):
        if score >= 96:
            return 1.0
        elif score >= 90:
            return 1.25
        elif score >= 84:
            return 1.5
        elif score >= 78:
            return 1.75
        elif score >= 72:
            return 2.0
        elif score >= 66:
            return 2.25
        elif score >= 60:
            return 2.5
        elif score >= 55:
            return 2.75
        elif score >= 50:
            return 3.0
        else:
            return 5.0

    for subject in subjects:
        grading_weight = GradingWeight.query.filter_by(
            instructor_id=instructor.id,
            subject_id=subject.id
        ).first()

        if not grading_weight:
            continue

        students = subject.students

        for student in students:
            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
            if grade:
                quiz = grade.total_quiz_score or 0
                assignment = grade.total_assignment_score or 0
                midterm = grade.midterm or 0
                finals = grade.finals or 0

                weighted_score = (
                    (quiz * grading_weight.quiz_weight) +
                    (assignment * grading_weight.assignment_weight) +
                    (midterm * grading_weight.midterm_weight) +
                    (finals * grading_weight.final_weight)
                )

                numeric_grade = calculate_numeric_grade(weighted_score)

                grade.grade = f"{numeric_grade:.2f}"
                grade.status = GradeStatus.GRADED
                db.session.commit()

        subject_students[subject] = students

    return render_template("instructor/student.html", subject_students=subject_students)



@bp.route("/instructor/record_assessments", methods=["GET"])
@login_required
def record_assessments():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        flash("Instructor profile not found.", "danger")
        return redirect(url_for("main.instructor_profile"))

    subject_section_students = {}

    for subject in instructor.subjects:
        # Query only students enrolled in this subject
        students = (
            Student.query
            .join(student_subject)
            .filter(student_subject.c.subject_id == subject.id)
            .all()
        )

        # Group students by year_and_section for this subject
        for student in students:
            section = student.year_and_section or "N/A"
            key = (subject, section)

            if key not in subject_section_students:
                subject_section_students[key] = []

            subject_section_students[key].append(student)

    # Unique sorted section list for filtering
    year_sections = sorted(set(section for (_, section) in subject_section_students.keys()))

    return render_template(
        "instructor/record_assessments.html",
        subject_section_students=subject_section_students,
        year_sections=year_sections
    )


@bp.route("/instructor/save_grading_weights", methods=["POST"])
@login_required
def save_grading_weights():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        flash("Instructor not found.", "danger")
        return redirect(url_for("main.instructor_students"))

    # Get form data from request.form (not JSON)
    try:
        quiz = int(request.form.get("quiz_weight", -1))
        assignment = int(request.form.get("assignment_weight", -1))
        midterm = int(request.form.get("midterm_weight", -1))
        finals = int(request.form.get("final_weight", -1))
    except ValueError:
        flash("Invalid input: weights must be integers.", "danger")
        return redirect(url_for("main.instructor_students"))

    if any(w < 0 for w in [quiz, assignment, midterm, finals]):
        flash("Missing required fields.", "danger")
        return redirect(url_for("main.instructor_students"))

    total = quiz + assignment + midterm + finals
    if total != 100:
        flash("Weights must total 100%.", "danger")
        return redirect(url_for("main.instructor_students"))

    # Apply to all subjects of the instructor (or add subject_id handling)
    subjects = instructor.subjects
    for subject in subjects:
        weight = GradingWeight.query.filter_by(instructor_id=instructor.id, subject_id=subject.id).first()
        if not weight:
            weight = GradingWeight(
                instructor_id=instructor.id,
                subject_id=subject.id,
            )
        weight.quiz_weight = quiz
        weight.assignment_weight = assignment
        weight.midterm_weight = midterm
        weight.final_weight = finals
        db.session.add(weight)
    db.session.commit()

    flash("Grading weights saved successfully!", "success")
    return redirect(url_for("main.instructor_students"))



@bp.route("/instructor/upload_excel_assessments", methods=["POST"])
@login_required
def upload_excel_assessments():
    file = request.files.get("excel_file")
    subject_id = int(request.form["subject_id"])
    year_section = request.form["year_section"]

    if not file:
        flash("No file uploaded", "danger")
        return redirect(url_for("main.record_assessments"))

    def to_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def to_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    try:
        df = pd.read_excel(file)

        # Expected columns:
        # student_no, Student Name, ..., Total Quiz, Total Assignment, Midterms, Finals

        for _, row in df.iterrows():
            student_no = str(row.get("student_no")).strip()
            if not student_no:
                continue  # Skip rows without student_no

            student = Student.query.filter_by(student_no=student_no).first()
            if not student:
                flash(f"Student with student_no '{student_no}' not found.", "warning")
                continue

            total_quiz_score = to_float(row.get("Total Quiz"))
            total_assignment_score = to_float(row.get("Total Assignment"))
            midterm_score = to_int(row.get("Midterms"))
            finals_score = to_int(row.get("Finals"))

            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject_id).first()
            if not grade:
                grade = Grade(student_id=student.id, subject_id=subject_id)
                db.session.add(grade)
                db.session.flush()

            grade.total_quiz_score = total_quiz_score
            grade.total_assignment_score = total_assignment_score
            grade.midterm = midterm_score
            grade.finals = finals_score

        db.session.commit()
        flash("Excel assessments uploaded successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error processing file: {e}", "danger")

    return redirect(url_for("main.record_assessments"))




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
        selected_subject_ids = request.form.getlist("subject_ids")

        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("main.instructor_profile"))

        instructor.name = name

        # Assign selected subjects to instructor
        selected_subjects = Subject.query.filter(Subject.id.in_(selected_subject_ids)).all()
        instructor.subjects = selected_subjects

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
@login_required
def student_profile():
    student = Student.query.filter_by(user_id=current_user.id).first()

    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        # Update fields with fallback to existing values
        student.name = request.form.get("name", student.name).strip()
        student.student_no = request.form.get("student_no", student.student_no).strip()
        student.year_and_section = request.form.get("year_and_section", student.year_and_section).strip()

        # Update subjects from checkboxes
        selected_subject_ids = request.form.getlist("subject_ids")
        try:
            selected_subject_ids = [int(sid) for sid in selected_subject_ids]
        except ValueError:
            selected_subject_ids = []

        selected_subjects = Subject.query.filter(Subject.id.in_(selected_subject_ids)).all()
        student.subjects = selected_subjects

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.student_profile"))

    # GET request: render profile form
    subjects = Subject.query.all()
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
        new_user.set_password(password)  # store plain text password as-is
        db.session.add(new_user)
        db.session.flush()  # to get new_user.id for FK relations

        # Create linked profile with empty/default name
        if role == "student":
            student = Student(user_id=new_user.id, name="")
            db.session.add(student)
        elif role == "instructor":
            instructor = Instructor(user_id=new_user.id, name="")
            db.session.add(instructor)

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
