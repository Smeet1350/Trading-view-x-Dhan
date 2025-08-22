"""
Phase 2 Tests: Webhook ingestion + idempotency
"""

import pytest
import tempfile
import os
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.webhook import TradingViewWebhook
from backend.app.services.alert_service import AlertService, reset_alert_service


class TestPhase02Webhook:
    """Test Phase 2: Webhook functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Setup test database for each test"""
        # Create a temporary database file for each test
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # Set environment variable for the test database
        os.environ["ALERT_DB_PATH"] = temp_db.name
        
        # Reset the global alert service instance
        reset_alert_service()
        
        yield
        
        # Clean up temporary database and environment variable
        try:
            os.unlink(temp_db.name)
        except:
            pass
        finally:
            if "ALERT_DB_PATH" in os.environ:
                del os.environ["ALERT_DB_PATH"]
            # Reset global instance
            reset_alert_service()
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def valid_webhook_data(self):
        """Valid webhook payload"""
        return {
            "id": "test-alert-001",
            "symbol": "NIFTY",
            "signal": "BUY CE",
            "ts": "2024-12-26T10:00:00"
        }
    
    def test_webhook_endpoint_exists(self, client):
        """Test that POST /webhook endpoint exists"""
        response = client.post("/webhook", json={})
        # Should get validation error, not 404
        assert response.status_code != 404
    
    def test_valid_input_accepted_and_saved(self, client, valid_webhook_data):
        """Test valid input accepted and saved"""
        headers = {"X-WEBHOOK-TOKEN": "test_webhook_token"}
        
        response = client.post("/webhook", json=valid_webhook_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["message"] == "Alert stored successfully"
    
    def test_duplicate_rejected_gracefully(self, client, valid_webhook_data):
        """Test duplicate rejected gracefully"""
        headers = {"X-WEBHOOK-TOKEN": "test_webhook_token"}
        
        # First request - should be accepted
        response1 = client.post("/webhook", json=valid_webhook_data, headers=headers)
        assert response1.status_code == 200
        assert response1.json()["status"] == "accepted"
        
        # Second request with same data - should be rejected as duplicate
        response2 = client.post("/webhook", json=valid_webhook_data, headers=headers)
        assert response2.status_code == 200
        assert response2.json()["status"] == "duplicate"
        assert response2.json()["message"] == "Alert already processed"
    
    def test_webhook_authentication_required(self, client, valid_webhook_data):
        """Test webhook authentication is required"""
        # No token header
        response = client.post("/webhook", json=valid_webhook_data)
        assert response.status_code == 401
        assert "Missing X-WEBHOOK-TOKEN header" in response.json()["detail"]
    
    def test_webhook_authentication_validated(self, client, valid_webhook_data):
        """Test webhook token validation"""
        # Invalid token
        headers = {"X-WEBHOOK-TOKEN": "invalid_token"}
        response = client.post("/webhook", json=valid_webhook_data, headers=headers)
        assert response.status_code == 401
        assert "Invalid webhook token" in response.json()["detail"]
    
    def test_webhook_payload_validation(self, client):
        """Test webhook payload validation"""
        headers = {"X-WEBHOOK-TOKEN": "test_webhook_token"}
        
        # Invalid symbol
        invalid_data = {
            "id": "test-001",
            "symbol": "INVALID",
            "signal": "BUY CE",
            "ts": "2024-12-26T10:00:00"
        }
        response = client.post("/webhook", json=invalid_data, headers=headers)
        assert response.status_code == 422  # Validation error
        
        # Invalid signal
        invalid_data = {
            "id": "test-001",
            "symbol": "NIFTY",
            "signal": "INVALID",
            "ts": "2024-12-26T10:00:00"
        }
        response = client.post("/webhook", json=invalid_data, headers=headers)
        assert response.status_code == 422  # Validation error
    
    def test_webhook_status_endpoint(self, client):
        """Test webhook status endpoint"""
        response = client.get("/webhook/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "active"
        assert data["phase"] == "2"
        assert "alert_count" in data
        assert "message" in data
    
    def test_root_endpoint_updated_for_phase_2(self, client):
        """Test root endpoint shows Phase 2 features"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["phase"] == "2"
        assert "TradingView webhook integration" in data["features"]
        assert "Alert idempotency with SHA256 hashing" in data["features"]
        assert "SQLite alert storage" in data["features"]


class TestPhase02AlertService:
    """Test Phase 2: Alert service functionality"""
    
    def test_alert_service_initialization(self):
        """Test alert service can be initialized"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            service = AlertService(db_path=temp_db.name)
            assert service is not None
        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass
    
    def test_alert_hash_computation(self):
        """Test SHA256 hash computation for idempotency"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            service = AlertService(db_path=temp_db.name)
            
            alert1 = TradingViewWebhook(
                id="test-001",
                symbol="NIFTY",
                signal="BUY CE",
                ts=datetime.fromisoformat("2024-12-26T10:00:00")
            )
            
            alert2 = TradingViewWebhook(
                id="test-001",
                symbol="NIFTY",
                signal="BUY CE",
                ts=datetime.fromisoformat("2024-12-26T10:00:00")
            )
            
            # Same alert should have same hash
            hash1 = service._compute_hash(alert1)
            hash2 = service._compute_hash(alert2)
            assert hash1 == hash2
            
            # Different alert should have different hash
            alert3 = TradingViewWebhook(
                id="test-002",
                symbol="NIFTY",
                signal="BUY CE",
                ts=datetime.fromisoformat("2024-12-26T10:00:00")
            )
            hash3 = service._compute_hash(alert3)
            assert hash1 != hash3
        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass
    
    def test_alert_storage_and_retrieval(self):
        """Test alert storage and duplicate detection"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            service = AlertService(db_path=temp_db.name)
            
            alert = TradingViewWebhook(
                id="test-001",
                symbol="NIFTY",
                signal="BUY CE",
                ts=datetime.fromisoformat("2024-12-26T10:00:00")
            )
            
            # Initially not duplicate
            assert not service.is_duplicate(alert)
            
            # Store alert
            assert service.store_alert(alert)
            
            # Now should be duplicate
            assert service.is_duplicate(alert)
            
            # Alert count should be 1
            assert service.get_alert_count() == 1
        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass
