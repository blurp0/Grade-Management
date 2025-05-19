from flask import Blueprint, render_template
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
    return render_template("student/home.html")

