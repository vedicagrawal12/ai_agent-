import time
# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from utils.task_runner import TaskRunner
from collectors.base_collector import Lead

def test_task_runner_success():
    """Verify TaskRunner runs a background job and updates status correctly on success."""
    def slow_add(a, b):
        time.sleep(0.1)
        return a + b
        
    task_id = TaskRunner.submit(slow_add, 10, 20)
    status = TaskRunner.get_status(task_id)
    assert status["status"] in ["RUNNING", "DONE"]
    
    # Wait for execution to finish
    time.sleep(0.2)
    status = TaskRunner.get_status(task_id)
    assert status["status"] == "DONE"
    assert status["result"] == 30
    assert status["error"] is None

def test_task_runner_failure():
    """Verify TaskRunner captures failure exceptions and updates status to FAILED."""
    def raise_error():
        time.sleep(0.05)
        raise ValueError("Simulated runner failure")
        
    task_id = TaskRunner.submit(raise_error)
    status = TaskRunner.get_status(task_id)
    assert status["status"] in ["RUNNING", "DONE", "FAILED"]
    
    # Wait for completion
    time.sleep(0.15)
    status = TaskRunner.get_status(task_id)
    assert status["status"] == "FAILED"
    assert "Simulated runner failure" in status["error"]
    assert status["result"] is None

@patch('extensions.collector.search')
def test_async_search_flow(mock_search, auth_client, db):
    """Verify API search endpoint triggers asynchronous search and status endpoint returns results."""
    mock_search.return_value = [
        Lead(name="Perf Gym", place_id="place_perf_test", city="Bhopal", phone="+91 98765 43210")
    ]
    
    # Configure dummy API key on the backend store to bypass key checks
    from extensions import API_KEY_STORE
    API_KEY_STORE["serpapi"] = "dummy-serp-key"
    
    resp = auth_client.post('/api/search', json={
        "query": "gyms",
        "city": "Bhopal",
        "max_results": 5
    })
    
    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert "task_id" in resp.json
    
    task_id = resp.json["task_id"]
    
    # Poll status endpoint until DONE
    for _ in range(10):
        status_resp = auth_client.get(f'/api/search/status/{task_id}')
        assert status_resp.status_code == 200
        if status_resp.json["status"] == "DONE":
            break
        time.sleep(0.1)
        
    status_resp = auth_client.get(f'/api/search/status/{task_id}')
    assert status_resp.json["status"] == "DONE"
    assert status_resp.json["result"]["query"] == "gyms in Bhopal"
    assert len(status_resp.json["result"]["leads"]) == 1
    assert status_resp.json["result"]["leads"][0]["name"] == "Perf Gym"

def test_database_and_api_pagination(auth_client, db):
    """Verify database pagination queries and leads endpoint page offsets."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Save 5 sample leads
    sample_leads = [
        Lead(name=f"Paginated Lead {i}", place_id=f"place_p_{i}", city="Bhopal")
        for i in range(1, 6)
    ]
    db.save_leads(sample_leads, user_id=user_id)
    
    # Test DB pagination directly
    res_page_1 = db.get_all_leads_paginated(user_id=user_id, page=1, per_page=2)
    assert len(res_page_1["leads"]) == 2
    assert res_page_1["total"] == 5
    assert res_page_1["page"] == 1
    assert res_page_1["per_page"] == 2
    assert res_page_1["pages"] == 3
    
    res_page_3 = db.get_all_leads_paginated(user_id=user_id, page=3, per_page=2)
    assert len(res_page_3["leads"]) == 1
    
    # Test API pagination route
    resp = auth_client.get('/api/leads?page=1&per_page=2')
    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert len(resp.json["leads"]) == 2
    assert resp.json["total"] == 5
    assert resp.json["page"] == 1
    assert resp.json["pages"] == 3

def test_health_endpoint(client):
    """Verify that /health is public and returns 200 with database status."""
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json["status"] == "healthy"
    assert resp.json["database"] == "connected"
