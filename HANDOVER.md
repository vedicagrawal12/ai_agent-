# LeadHunter AI — Tech Handover Document

Welcome! If you are reading this, you are taking over the technical management of the LeadHunter AI project. This document summarizes the current state of the application, recent deployment fixes, and how to manage it moving forward.

## 🏗 Architecture Overview
- **Framework:** Python (Flask)
- **Database:** PostgreSQL (Render hosted) & local SQLite support (`database.py`)
- **Background Tasks:** The application originally used Celery and Redis. However, to fit within Render's Free Tier limits, **Celery has been disabled** (`CELERY_ENABLED=false`). The app currently falls back to native Python background threading (`utils/imap_reader.py` and `utils/drip_scheduler.py`) which runs inside the Flask process.
- **Hosting:** Render (Web Service + PostgreSQL)
- **Deployment:** Connected to GitHub for automatic deployments via `render.yaml` blueprint.

## 🚀 Recent Deployment Fixes (What was just done)
1. **Render Blueprint (`render.yaml`)**: We created a Render blueprint to automate deployment. We specifically stripped out the Redis and Celery worker services because Render does not allow background workers on the free tier.
2. **Reverse Proxy Fix (`app.py`)**: The application uses `Flask-Limiter`. Because Render sits behind a load balancer, all incoming traffic appeared as `127.0.0.1`, causing the rate limiter to instantly block users. We added `werkzeug.middleware.proxy_fix.ProxyFix` to `app.py` to correctly resolve actual client IP addresses.
3. **GitHub Security Bypass**: The `test_harness.py` and `README.md` files contain GCP API keys. GitHub's Secret Scanner initially blocked the push, but the repository owner has whitelisted these secrets to allow pushing.

## 💻 Local Development Setup
To run this project on your local machine:
1. Clone the repository from GitHub.
2. Create a virtual environment: `python -m venv venv`
3. Activate it and install requirements: `pip install -r requirements.txt`
4. Set up your `.env` file (copy from `.env.example`).
5. Run the app: `python app.py`

## 🌍 Managing the Live Deployment
The live application is hosted on **Render**. 
- It is connected to the `main` branch of this GitHub repository.
- **Continuous Deployment (CI/CD):** Any time you `git push` changes to the `main` branch on GitHub, Render will automatically detect the changes, pull the new code, and redeploy the live website. You do not need to manually push to Render.
- **Environment Variables:** Secrets like `SERPAPI_KEY` are stored in the Render Dashboard under the `leadhunter-web` service's "Environment" tab. Do not commit sensitive keys directly to the codebase.

## 🤝 Collaboration (How the owner stays connected)
The original owner wants to stay connected and see the changes you make:
1. **Code Visibility:** As long as you push your code updates to this GitHub repository, the owner can log into GitHub at any time to see a history of all changes, which lines of code were modified, and when.
2. **Live Updates:** Because Render is linked to GitHub, the owner can simply visit the live Render URL to see your new features working in real-time as soon as you push them.
