import logging
import re
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, limiter, cache
from utils.security import login_tracker

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html")
        
        # Account lockout check by email
        if login_tracker.is_locked(email):
            remaining = login_tracker.remaining_lockout(email)
            logger.warning(f"Login attempt on locked account: {email} ({remaining}s remaining)")
            flash(f"Account temporarily locked. Try again in {remaining} seconds.", "error")
            return render_template("login.html")
            
        user = db.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            if not user.get("is_active", True):
                logger.warning(f"Deactivated user login attempt: {email}")
                flash("Your account has been deactivated. Please contact an admin.", "error")
                return render_template("login.html")
            login_tracker.clear(email)  # Reset failed attempts on success
            session.clear()
            session.permanent = True  # Activates PERMANENT_SESSION_LIFETIME (24hr expiry)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            logger.info(f"User logged in: {user['username']} ({email})")
            return redirect(url_for('dashboard.index'))
        else:
            login_tracker.record_failure(email)
            logger.warning(f"Failed login attempt for: {email}")
            flash("Invalid email or password.", "error")
            
    return render_template("login.html")

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("60 per hour", methods=["POST"])
def signup():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        
        if not username or not email or not password or not phone:
            flash("Username, email, password, and contact number are required.", "error")
            return render_template("signup.html")
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Please enter a valid email address (e.g. name@example.com).", "error")
            return render_template("signup.html")
            
        # Validate phone format
        phone_regex = r'^\+?[0-9\s\-()]{7,20}$'
        if not re.match(phone_regex, phone):
            flash("Please enter a valid contact number.", "error")
            return render_template("signup.html")
        
        # Enforce password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
            
        # Check if email already exists (multiple duplicate usernames are allowed)
        existing_user = db.get_user_by_email(email)
        if existing_user:
            flash("Email address is already registered.", "error")
            return render_template("signup.html")
            
        # Create user
        password_hash = generate_password_hash(password, method='scrypt')
        success = db.create_user(username, email, password_hash, phone)
        if success:
            from utils.email_sender import send_welcome_email
            send_welcome_email(email, username)
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

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == "POST":
        from utils.email_sender import is_smtp_configured
        if not is_smtp_configured():
            flash("System email service is not configured on the server. Please contact an admin.", "error")
            return render_template("forgot_password.html")
            
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Email address is required.", "error")
            return render_template("forgot_password.html")
            
        user = db.get_user_by_email(email)
        if not user:
            flash("Email address is not registered.", "error")
            return render_template("forgot_password.html")
            
        import random
        from datetime import datetime, timedelta
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=10)
        
        success = db.save_password_reset_otp(email, otp, expires_at)
        if success:
            cache.delete(f"otp_failures_{email}")
            from utils.email_sender import send_otp_email
            send_otp_email(email, otp)
            session["reset_email"] = email
            flash("Verification OTP has been sent to your email address.", "success")
            return redirect(url_for('auth.verify_otp'))
        else:
            flash("Failed to process request. Please try again.", "error")
            
    return render_template("forgot_password.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def verify_otp():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    email = session.get("reset_email")
    if not email:
        flash("Please enter your email to request an OTP first.", "error")
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        if not otp:
            flash("OTP is required.", "error")
            return render_template("verify_otp.html")
            
        is_valid = db.verify_password_reset_otp(email, otp)
        if is_valid:
            session["otp_verified"] = True
            cache.delete(f"otp_failures_{email}")
            flash("OTP verified successfully. Please choose a new password.", "success")
            return redirect(url_for('auth.reset_password'))
        else:
            failures = cache.get(f"otp_failures_{email}") or 0
            failures += 1
            if failures >= 5:
                db.delete_password_reset_otp(email)
                cache.delete(f"otp_failures_{email}")
                session.pop("reset_email", None)
                flash("Too many failed attempts. Please request a new OTP.", "error")
                return redirect(url_for('auth.forgot_password'))
            else:
                cache.set(f"otp_failures_{email}", failures, timeout=600)
                flash("Invalid or expired OTP. Please try again.", "error")
            
    return render_template("verify_otp.html")

@auth_bp.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password():
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    email = session.get("reset_email")
    otp_verified = session.get("otp_verified")
    if not email or not otp_verified:
        flash("Unauthorized access. Please verify your OTP first.", "error")
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not password or not confirm_password:
            flash("Password and confirmation are required.", "error")
            return render_template("reset_password.html")
            
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("reset_password.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html")
            
        # Perform reset
        password_hash = generate_password_hash(password, method='scrypt')
        success = db.update_user_password(email, password_hash)
        if success:
            db.delete_password_reset_otp(email)
            session.pop("reset_email", None)
            session.pop("otp_verified", None)
            flash("Password has been reset successfully. Please log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Failed to update password. Please try again.", "error")
            
    return render_template("reset_password.html")
