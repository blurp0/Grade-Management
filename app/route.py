from flask import Blueprint, render_template
from flask_login import current_user
from app.model import Student

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("base.html")


# Auth (Login/Register)



# Instructor Navigation

@bp.route("/instructor")
def instructor():
    return render_template("instructor/home.html")



# Student Navigation

@bp.route("/student")
def student():

    student = Student.query.filter_by(user_id=current_user.id).first()
    return render_template("student/home.html", student=student)

