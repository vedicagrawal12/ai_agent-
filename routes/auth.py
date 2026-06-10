import logging
import re
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, limiter
from utils.security import login_tracker

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")
        
        # Account lockout check
        if login_tracker.is_locked(username):
            remaining = login_tracker.remaining_lockout(username)
            logger.warning(f"Login attempt on locked account: {username} ({remaining}s remaining)")
            flash(f"Account temporarily locked. Try again in {remaining} seconds.", "error")
            return render_template("login.html")
            
        user = db.get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            if not user.get("is_active", True):
                logger.warning(f"Deactivated user login attempt: {username}")
                flash("Your account has been deactivated. Please contact an admin.", "error")
                return render_template("login.html")
            login_tracker.clear(username)  # Reset failed attempts on success
            session.clear()
            session.permanent = True  # Activates PERMANENT_SESSION_LIFETIME (24hr expiry)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            logger.info(f"User logged in: {username}")
            return redirect(url_for('dashboard.index'))
        else:
            login_tracker.record_failure(username)
            logger.warning(f"Failed login attempt for: {username}")
            flash("Invalid username or password.", "error")
            
    return render_template("login.html")

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("60 per hour", methods=["POST"])
def signup():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not username or not email or not password:
            flash("Username, email, and password are required.", "error")
            return render_template("signup.html")
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Please enter a valid email address (e.g. name@example.com).", "error")
            return render_template("signup.html")
        
        # Enforce password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
            
        # Check if user already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            flash("Username already exists.", "error")
            return render_template("signup.html")
            
        # Create user
        password_hash = generate_password_hash(password)
        success = db.create_user(username, email, password_hash)
        if success:
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Failed to create account. Please try again.", "error")
            
    return render_template("signup.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('auth.login'))
