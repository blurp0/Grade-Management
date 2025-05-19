from flask import Blueprint, render_template
from flask_login import current_user
from app.model import Student

bp = Blueprint("main", __name__)

from flask import Blueprint, request, redirect, url_for, render_template, flash, session
from .model import User
from . import db
bp = Blueprint("main", __name__)

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("main.register"))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Login successful!")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid username or password")

    return render_template("login.html")

@bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("main.login"))
    return render_template("base.html")

@bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.")
    return redirect(url_for("main.login"))

@bp.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))



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

