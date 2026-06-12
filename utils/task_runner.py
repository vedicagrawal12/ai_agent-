import threading
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class TaskRunner:
    """Simple in-process background task runner using threads."""
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def _cleanup_expired_tasks(cls):
        """Clean up tasks older than 1 hour to prevent memory leak."""
        with cls._lock:
            now = datetime.now()
            expired_ids = [
                tid for tid, task in cls._tasks.items()
                if (now - task["started_at"]).total_seconds() > 3600
            ]
            for tid in expired_ids:
                cls._tasks.pop(tid, None)
                
    @classmethod
    def submit(cls, func: Callable, *args, **kwargs) -> str:
        """
        Submit a function to run in the background.
        Returns a task ID string.
        """
        cls._cleanup_expired_tasks()
        task_id = str(uuid.uuid4())[:8]
        
        with cls._lock:
            cls._tasks[task_id] = {
                "status": "RUNNING",
                "result": None,
                "error": None,
                "started_at": datetime.now()
            }
            
        def wrapper():
            try:
                logger.info(f"[TaskRunner] Starting background task {task_id}...")
                result = func(*args, **kwargs)
                with cls._lock:
                    cls._tasks[task_id]["status"] = "DONE"
                    cls._tasks[task_id]["result"] = result
                logger.info(f"[TaskRunner] Completed background task {task_id} successfully.")
            except Exception as e:
                logger.exception(f"[TaskRunner] Task {task_id} failed with error: {e}")
                with cls._lock:
                    cls._tasks[task_id]["status"] = "FAILED"
                    cls._tasks[task_id]["error"] = str(e)
        
        # Start execution in daemon thread
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        
        # Automatic self-cleanup after 1 hour to prevent memory leaks if never polled
        def self_cleanup():
            with cls._lock:
                cls._tasks.pop(task_id, None)
        
        cleanup_timer = threading.Timer(3600.0, self_cleanup)
        cleanup_timer.daemon = True
        cleanup_timer.start()
        
        return task_id
        
    @classmethod
    def get_status(cls, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of the task.
        Also cleans up tasks older than 1 hour.
        """
        cls._cleanup_expired_tasks()
        with cls._lock:
            return cls._tasks.get(task_id, {"status": "NOT_FOUND"})
