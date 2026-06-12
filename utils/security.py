"""
Login Attempt Tracker — Account lockout after repeated failed login attempts.

Prevents brute-force password guessing by tracking failed attempts per username.
After MAX_ATTEMPTS failures within LOCKOUT_SECONDS, the account is temporarily locked.
"""

import time
from collections import defaultdict
import threading
from constants import LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS


class LoginTracker:
    """Thread-safe login attempt tracker with automatic lockout."""
    
    MAX_ATTEMPTS = LOGIN_MAX_ATTEMPTS          # Lock attempts limit
    LOCKOUT_SECONDS = LOGIN_LOCKOUT_SECONDS     # Lock duration seconds

    def __init__(self):
        self._attempts = defaultdict(list)  # username -> [timestamp, ...]
        self._lock = threading.Lock()

    def is_locked(self, username: str) -> bool:
        """Check if a username is currently locked out."""
        with self._lock:
            attempts = self._attempts.get(username, [])
            # Remove attempts older than lockout window
            now = time.time()
            recent = [t for t in attempts if now - t < self.LOCKOUT_SECONDS]
            self._attempts[username] = recent
            return len(recent) >= self.MAX_ATTEMPTS

    def _cleanup_all(self):
        """Evict all expired attempt entries to prevent unbounded memory growth."""
        now = time.time()
        expired_keys = []
        for username, attempts in self._attempts.items():
            recent = [t for t in attempts if now - t < self.LOCKOUT_SECONDS]
            if recent:
                self._attempts[username] = recent
            else:
                expired_keys.append(username)
        for key in expired_keys:
            del self._attempts[key]

    def record_failure(self, username: str):
        """Record a failed login attempt."""
        with self._lock:
            self._attempts[username].append(time.time())
            # Periodic global cleanup to prevent memory leak under brute-force
            if len(self._attempts) > 100:
                self._cleanup_all()

    def clear(self, username: str):
        """Clear all attempts on successful login."""
        with self._lock:
            self._attempts.pop(username, None)

    def remaining_lockout(self, username: str) -> int:
        """Get remaining lockout time in seconds."""
        with self._lock:
            attempts = self._attempts.get(username, [])
            if len(attempts) < self.MAX_ATTEMPTS:
                return 0
            oldest_relevant = sorted(attempts)[-self.MAX_ATTEMPTS]
            return max(0, int(self.LOCKOUT_SECONDS - (time.time() - oldest_relevant)))


# Singleton instance used across the app
login_tracker = LoginTracker()
