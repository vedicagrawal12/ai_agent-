# celery_worker.py
from app import create_app
# pyrefly: ignore [missing-import]
from celery import Celery

# Create the Flask application instance
app = create_app()

# Initialize Celery app
celery_app = Celery(
    app.import_name,
    backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
)

# Filter and map Flask configurations to Celery native settings to avoid configuration naming errors.
celery_conf = {
    'broker_url': app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    'result_backend': app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
}
celery_app.conf.update(celery_conf)

# Wrap task executions within Flask's Application Context
class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            try:
                return self.run(*args, **kwargs)
            finally:
                try:
                    from extensions import db
                    db.remove_session()
                except Exception as teardown_err:
                    app.logger.error(f"Error during celery task session teardown: {teardown_err}")

celery_app.Task = ContextTask

# Define Tasks

@celery_app.task(name="run_background_search_task")
def run_background_search_task(*args, **kwargs):
    from routes.api_leads import run_background_search
    return run_background_search(*args, **kwargs)

@celery_app.task(name="sync_all_imap_replies_task")
def sync_all_imap_replies_task():
    from utils.imap_reader import sync_user_replies
    from database import Database
    db = Database()
    conn = db._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT user_id FROM imap_settings;")
        users = cursor.fetchall()
    finally:
        db._release_connection(conn)
    
    for u in users:
        sync_user_replies(u[0])

@celery_app.task(name="dispatch_all_drip_campaigns_task")
def dispatch_all_drip_campaigns_task():
    from utils.drip_scheduler import process_drip_outreach_for_user
    from database import Database
    db = Database()
    conn = db._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT user_id FROM drip_configurations WHERE is_enabled = TRUE;")
        users = cursor.fetchall()
    finally:
        db._release_connection(conn)
        
    for u in users:
        process_drip_outreach_for_user(u[0])

# Configure Celery Beat Periodic Schedule
celery_app.conf.beat_schedule = {
    'sync-imap-replies-every-5-min': {
        'task': 'sync_all_imap_replies_task',
        'schedule': 300.0,  # 5 minutes (300s)
    },
    'dispatch-drips-every-hour': {
        'task': 'dispatch_all_drip_campaigns_task',
        'schedule': 3600.0,  # 1 hour (3600s)
    },
}
