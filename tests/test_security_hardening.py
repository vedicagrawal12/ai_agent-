# pyrefly: ignore [missing-import]
import pytest
import ssl
from unittest.mock import patch, MagicMock
from database import Database
from utils.email_scraper import EmailScraper
from utils.portfolio import PortfolioParser, SafeRedirectHandler

def test_encryption_backwards_compatibility():
    """Verify that new Fernet decryption successfully falls back to legacy XOR decryption."""
    db = Database()
    original_pass = "my_secret_smtp_pass_123"

    # 1. Manually encrypt using the old XOR algorithm to simulate legacy stored password
    from config import Config
    import hashlib, base64
    key_source = Config.SECRET_KEY or "fallback_secret_key_1234567890_!"
    key = hashlib.sha256(key_source.encode('utf-8')).digest()
    xor_encrypted_bytes = bytes(a ^ b for a, b in zip(original_pass.encode('utf-8'), key * (len(original_pass) // len(key) + 1)))
    xor_encrypted_str = base64.b64encode(xor_encrypted_bytes).decode('utf-8')

    # Verify fallback decryption resolves this legacy XOR string
    decrypted_xor = db._decrypt_password(xor_encrypted_str)
    assert decrypted_xor == original_pass

    # 2. Encrypt using the new Fernet-based helper
    fernet_encrypted_str = db._encrypt_password(original_pass)
    assert fernet_encrypted_str != xor_encrypted_str

    # Verify Fernet decryption resolves this new string
    decrypted_fernet = db._decrypt_password(fernet_encrypted_str)
    assert decrypted_fernet == original_pass

def test_ssrf_redirect_blocking_email_scraper():
    """Verify that EmailScraper._get_safe_response blocks HTTP redirects to private/loopback targets."""
    # Mock requests.get to return a redirect to local resource
    mock_redirect = MagicMock()
    mock_redirect.is_redirect = True
    mock_redirect.status_code = 302
    mock_redirect.headers = {"Location": "http://127.0.0.1:5432/admin"}

    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_redirect

        with pytest.raises(Exception) as exc_info:
            EmailScraper._get_safe_response("https://safe-public-domain.com", headers={})

        assert "Blocked request to unsafe URL" in str(exc_info.value)
        assert "127.0.0.1" in str(exc_info.value)

def test_ssrf_redirect_blocking_portfolio_parser():
    """Verify that SafeRedirectHandler raises HTTPError when redirect targets private/loopback IPs."""
    handler = SafeRedirectHandler()
    mock_req = MagicMock()
    mock_req.full_url = "https://safe-public-domain.com"
    
    # Attempt redirect to loopback IP
    with pytest.raises(Exception) as exc_info:
        handler.redirect_request(mock_req, None, 302, "Found", {}, "http://localhost:5000/private")
        
    assert "Redirect to unsafe URL blocked" in str(exc_info.value)

def test_celery_task_routing_and_status():
    """Verify that TaskRunner routes submissions to Celery and queries AsyncResult when CELERY_ENABLED is active."""
    from utils.task_runner import TaskRunner
    from flask import Flask
    
    app = Flask("test_app")
    app.config["CELERY_ENABLED"] = True
    
    mock_task_id = "test-celery-uuid"
    
    with app.app_context():
        with patch("celery_worker.run_background_search_task.delay") as mock_delay, \
             patch("celery.result.AsyncResult") as mock_async_result:
            
            mock_delay.return_value.id = mock_task_id
            
            task_id = TaskRunner.submit(lambda: "search_businesses", query="gym", city="Bhopal")
            assert task_id == mock_task_id
            mock_delay.assert_called_once_with(query="gym", city="Bhopal")
            
            mock_result_instance = MagicMock()
            mock_result_instance.state = "SUCCESS"
            mock_result_instance.result = {"leads": []}
            mock_async_result.return_value = mock_result_instance
            
            status_info = TaskRunner.get_status(mock_task_id)
            assert status_info["status"] == "DONE"
            assert status_info["result"] == {"leads": []}
