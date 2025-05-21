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


from sqlalchemy import func, distinct, cast, Float

@bp.route("/instructor")
@login_required
def instructor():
    instructor = Instructor.query.filter_by(user_id=current_user.id).first()
    if not instructor:
        return "Instructor profile not found", 404

    subject_ids = [subject.id for subject in (instructor.subjects or [])]
    num_subjects = len(subject_ids)

    if not subject_ids:
        passed_count = 0
        failed_count = 0
        top_student_name = None
        total_students = 0
    else:
        # Query grades with student names
        all_grades = (
            db.session.query(Grade.grade, Student.name, Grade.student_id)
            .join(Student, Grade.student_id == Student.id)
            .filter(
                Grade.subject_id.in_(subject_ids),
                Grade.grade.isnot(None)
            )
            .all()
        )

        passed_count = 0
        failed_count = 0
        highest_grade = None
        top_student_name = None

        # To count unique students
        student_ids_set = set()

        for grade_str, student_name, student_id in all_grades:
            try:
                numeric = float(grade_str)
                if numeric <= 3.00:
                    passed_count += 1
                else:
                    failed_count += 1

                if (highest_grade is None) or (numeric < highest_grade):
                    highest_grade = numeric
                    top_student_name = student_name

                student_ids_set.add(student_id)

            except ValueError:
                continue

        total_students = len(student_ids_set)

    return render_template(
        "instructor/home.html",
        instructor=instructor,
        passed_count=passed_count,
        failed_count=failed_count,
        top_student_name=top_student_name,
        total_students=total_students,
        num_subjects=num_subjects
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

    def safe_division(numerator, denominator):
        return (numerator / denominator) if denominator else 0

    def convert_to_grade_point(percent):
        if percent >= 96:
            return "1.00"
        elif percent >= 93:
            return "1.25"
        elif percent >= 90:
            return "1.50"
        elif percent >= 87:
            return "1.75"
        elif percent >= 84:
            return "2.00"
        elif percent >= 81:
            return "2.25"
        elif percent >= 78:
            return "2.50"
        elif percent >= 75:
            return "2.75"
        elif percent >= 70:
            return "3.00"
        elif percent >= 60:
            return "4.00"
        else:
            return "5.00"  # Failing grade

    for subject in subjects:
        grading_weight = GradingWeight.query.filter_by(
            instructor_id=instructor.id,
            subject_id=subject.id
        ).first()

        students_with_grades = []

        for student in subject.students:
            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()

            if grade and grading_weight:
                quiz_percent = safe_division(grade.total_quiz_score, grade.quiz_items)
                assignment_percent = safe_division(grade.total_assignment_score, grade.assignment_items)
                midterm_percent = safe_division(grade.midterm, grade.midterm_items)
                final_percent = safe_division(grade.finals, grade.final_items)

                final_grade = (
                    (quiz_percent * grading_weight.quiz_weight) +
                    (assignment_percent * grading_weight.assignment_weight) +
                    (midterm_percent * grading_weight.midterm_weight) +
                    (final_percent * grading_weight.final_weight)
                ) * 100

                grade.grade = convert_to_grade_point(final_grade)
                db.session.add(grade)  # Mark grade for update

            students_with_grades.append({
                "student": student,
                "grade": grade
            })

        subject_students[subject] = students_with_grades

    db.session.commit()

    return render_template(
        "instructor/student.html",
        subject_students=subject_students
    )


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

    # Convert to decimal (0.0 to 1.0)
    quiz_weight = quiz / 100
    assignment_weight = assignment / 100
    midterm_weight = midterm / 100
    final_weight = finals / 100

    # Apply weights to each subject
    subjects = instructor.subjects
    for subject in subjects:
        weight = GradingWeight.query.filter_by(instructor_id=instructor.id, subject_id=subject.id).first()
        if not weight:
            weight = GradingWeight(
                instructor_id=instructor.id,
                subject_id=subject.id,
            )
        weight.quiz_weight = quiz_weight
        weight.assignment_weight = assignment_weight
        weight.midterm_weight = midterm_weight
        weight.final_weight = final_weight
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

        # Read total item counts from first row
        quiz_items = to_int(df.get("Total Quiz Items")[0]) if "Total Quiz Items" in df.columns else 0
        assignment_items = to_int(df.get("Total Assignment Items")[0]) if "Total Assignment Items" in df.columns else 0
        midterm_items = to_int(df.get("Midterms Items")[0]) if "Midterms Items" in df.columns else 0
        final_items = to_int(df.get("Finals Items")[0]) if "Finals Items" in df.columns else 0

        print("Total Quiz Items:", quiz_items)
        print("Total Assignment Items:", assignment_items)
        print("Midterm Items:", midterm_items)
        print("Finals Items:", final_items)

        for _, row in df.iterrows():
            student_no = str(row.get("student_no")).strip()
            if not student_no:
                continue

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

            # Set assessment scores
            grade.total_quiz_score = total_quiz_score
            grade.total_assignment_score = total_assignment_score
            grade.midterm = midterm_score
            grade.finals = finals_score

            # Set item counts (same for all students in the file)
            grade.quiz_items = quiz_items
            grade.assignment_items = assignment_items
            grade.midterm_items = midterm_items
            grade.final_items = final_items

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
