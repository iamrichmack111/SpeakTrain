from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db


bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = get_db().execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone() if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            return "Administrator access required.", 403
        return view(**kwargs)
    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if len(username) < 2:
            error = "Username must contain at least two characters."
        elif len(password) < 6:
            error = "Password must contain at least six characters."
        elif get_db().execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            error = "That username is already registered."
        if error is None:
            role = "admin" if not get_db().execute("SELECT 1 FROM users LIMIT 1").fetchone() else "student"
            cursor = get_db().execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, generate_password_hash(password), role))
            user_id = cursor.lastrowid
            get_db().execute("UPDATE attempts SET user_id = ? WHERE user_id IS NULL", (user_id,))
            get_db().commit()
            session.clear();session["user_id"] = user_id
            return redirect(url_for("main.index"))
        flash(error)
    return render_template("auth.html", mode="register")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear();session["user_id"] = user["id"]
            return redirect(url_for("main.index"))
        flash("Incorrect username or password.")
    return render_template("auth.html", mode="login")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
