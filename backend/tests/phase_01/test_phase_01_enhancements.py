"""
Phase 1 Tests: FastAPI Skeleton & Health Endpoint Enhancements

Tests to verify:
- Configuration management system
- Enhanced logging functionality
- Comprehensive health check endpoints
- Custom exception handling
- Middleware functionality
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.logging import get_logger, setup_logging
from backend.app.main import app
from backend.app.models.health import ComponentStatus, HealthStatus
from backend.app.services.health_service import HealthService


class TestPhase01Configuration:
    """Test Phase 1: Configuration Management"""

    def test_settings_creation(self):
        """Test that settings can be created with defaults"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            settings = get_settings()
            assert settings.app_name == "TradingView x Dhan Trading System"
            assert settings.app_version == "0.1.0"
            assert settings.app_phase == "1"
            assert settings.webhook_token == "test_webhook"
            assert settings.admin_token == "test_admin"

    def test_settings_validation(self):
        """Test that settings validation works correctly"""
        with patch.dict(
            "os.environ",
            {
                "WEBHOOK_TOKEN": "test_webhook",
                "ADMIN_TOKEN": "test_admin",
                "LOG_LEVEL": "INVALID_LEVEL",
            },
        ):
            with pytest.raises(ValueError, match="Log level must be one of"):
                get_settings()

    def test_cors_configuration(self):
        """Test that CORS configuration is properly loaded"""
        with patch.dict(
            "os.environ",
            {
                "WEBHOOK_TOKEN": "test_webhook",
                "ADMIN_TOKEN": "test_admin",
                "CORS_ORIGINS": "http://localhost:3000",
            },
        ):
            settings = get_settings()
            assert "http://localhost:3000" in settings.cors_origins


class TestPhase01Logging:
    """Test Phase 1: Logging System"""

    def test_logger_creation(self):
        """Test that loggers can be created"""
        logger = get_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_logging_setup(self):
        """Test that logging setup can be called"""
        # This should not raise any exceptions
        setup_logging(log_level="INFO")


class TestPhase01HealthService:
    """Test Phase 1: Health Service"""

    @pytest.fixture
    def health_service(self):
        """Create a health service instance for testing"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            return HealthService()

    @pytest.mark.asyncio
    async def test_health_service_creation(self, health_service):
        """Test that health service can be created"""
        assert health_service is not None
        assert health_service.settings is not None

    @pytest.mark.asyncio
    async def test_basic_health_check(self, health_service):
        """Test basic health check functionality"""
        response = await health_service.perform_health_check(detailed=False)

        assert response is not None
        assert response.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert response.system_info.app_name == "TradingView x Dhan Trading System"
        assert response.system_info.phase == "1"
        assert len(response.components) > 0

    @pytest.mark.asyncio
    async def test_component_health_checks(self, health_service):
        """Test individual component health checks"""
        # Test system component
        system_status = await health_service._check_system()
        assert system_status.name == "system"
        assert system_status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        # Test configuration component
        config_status = await health_service._check_configuration()
        assert config_status.name == "configuration"
        assert config_status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        # Test dependencies component
        deps_status = await health_service._check_dependencies()
        assert deps_status.name == "dependencies"
        assert deps_status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_uptime_calculation(self, health_service):
        """Test uptime calculation"""
        uptime = health_service.get_uptime_seconds()
        assert uptime >= 0
        assert isinstance(uptime, float)

    def test_overall_status_calculation(self, health_service):
        """Test overall status calculation logic"""
        # Test with all healthy components
        healthy_components = [
            ComponentStatus(name="test1", status=HealthStatus.HEALTHY, message="OK"),
            ComponentStatus(name="test2", status=HealthStatus.HEALTHY, message="OK"),
        ]
        status = health_service._calculate_overall_status(healthy_components)
        assert status == HealthStatus.HEALTHY

        # Test with degraded component
        degraded_components = [
            ComponentStatus(name="test1", status=HealthStatus.HEALTHY, message="OK"),
            ComponentStatus(
                name="test2", status=HealthStatus.DEGRADED, message="Warning"
            ),
        ]
        status = health_service._calculate_overall_status(degraded_components)
        assert status == HealthStatus.DEGRADED

        # Test with unhealthy component
        unhealthy_components = [
            ComponentStatus(name="test1", status=HealthStatus.HEALTHY, message="OK"),
            ComponentStatus(
                name="test2", status=HealthStatus.UNHEALTHY, message="Error"
            ),
        ]
        status = health_service._calculate_overall_status(unhealthy_components)
        assert status == HealthStatus.UNHEALTHY


class TestPhase01APIEndpoints:
    """Test Phase 1: Enhanced API Endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked environment"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            return TestClient(app)

    def test_root_endpoint_enhanced(self, client):
        """Test enhanced root endpoint"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "TradingView x Dhan Trading System"
        assert data["phase"] == "1"
        assert data["status"] == "operational"
        assert "features" in data
        assert "endpoints" in data
        assert "Enhanced health monitoring" in data["features"]

    def test_legacy_healthz_endpoint(self, client):
        """Test legacy healthz endpoint for backward compatibility"""
        response = client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "1"
        assert "redirect" in data
        assert data["redirect"] == "/health"

    def test_enhanced_health_endpoint(self, client):
        """Test enhanced health endpoint"""
        response = client.get("/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["phase"] == "1"
        assert "status" in data
        assert "system_info" in data
        assert "components" in data
        assert "summary" in data

    def test_simple_health_endpoint(self, client):
        """Test simple health endpoint"""
        response = client.get("/health/simple")
        assert response.status_code in [200, 503]  # Can be either depending on health

        data = response.json()
        assert data["phase"] == "1"
        assert "status" in data
        assert "timestamp" in data

    def test_readiness_endpoint(self, client):
        """Test readiness endpoint"""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]  # Can be either depending on health

        data = response.json()
        assert data["phase"] == "1"
        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data

    def test_liveness_endpoint(self, client):
        """Test liveness endpoint"""
        response = client.get("/health/live")
        assert response.status_code in [200, 503]  # Can be either depending on health

        data = response.json()
        assert data["phase"] == "1"
        assert "alive" in data
        assert "status" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data

    def test_health_components_endpoint(self, client):
        """Test health components listing endpoint"""
        response = client.get("/health/components")
        assert response.status_code == 200

        data = response.json()
        assert data["phase"] == "1"
        assert "components" in data
        assert "total" in data
        assert len(data["components"]) > 0

        # Check that critical components are marked
        critical_components = [comp for comp in data["components"] if comp["critical"]]
        assert len(critical_components) > 0

    def test_orders_endpoint_enhanced(self, client):
        """Test enhanced orders endpoint"""
        response = client.get("/orders")
        assert response.status_code == 200

        data = response.json()
        assert data["phase"] == "1"
        assert "orders" in data
        assert "message" in data
        assert data["message"] == "Orders functionality coming in Phase 2"

    def test_response_headers(self, client):
        """Test that custom response headers are added"""
        response = client.get("/")
        assert response.status_code == 200

        # Check for custom headers
        assert "X-Process-Time" in response.headers
        assert "X-Phase" in response.headers
        assert response.headers["X-Phase"] == "1"


class TestPhase01Middleware:
    """Test Phase 1: Middleware Functionality"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked environment"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            return TestClient(app)

    def test_process_time_header(self, client):
        """Test that process time header is added"""
        response = client.get("/")
        assert "X-Process-Time" in response.headers

        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
        assert process_time < 1.0  # Should be very fast for simple endpoint

    def test_phase_header(self, client):
        """Test that phase header is added"""
        response = client.get("/")
        assert "X-Phase" in response.headers
        assert response.headers["X-Phase"] == "1"


class TestPhase01ErrorHandling:
    """Test Phase 1: Error Handling and Exceptions"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked environment"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            return TestClient(app)

    def test_404_error_handling(self, client):
        """Test 404 error handling"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["phase"] == "1"

    def test_validation_error_handling(self, client):
        """Test validation error handling"""
        # Test with invalid POST data to trigger Pydantic validation
        response = client.post("/health/check", json={"timeout_seconds": "invalid"})
        assert response.status_code == 422

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["phase"] == "1"


class TestPhase01Integration:
    """Test Phase 1: Integration and End-to-End Functionality"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked environment"""
        with patch.dict(
            "os.environ", {"WEBHOOK_TOKEN": "test_webhook", "ADMIN_TOKEN": "test_admin"}
        ):
            return TestClient(app)

    def test_application_startup(self, client):
        """Test that application starts up correctly"""
        response = client.get("/")
        assert response.status_code == 200

        # Check that all expected endpoints are documented
        data = response.json()
        assert "endpoints" in data
        endpoints = data["endpoints"]

        # Verify health endpoints
        assert endpoints["health"] == "/health"

        # Test that health endpoints are accessible
        health_response = client.get("/health/")
        assert health_response.status_code == 200

    def test_health_check_comprehensive(self, client):
        """Test comprehensive health check functionality"""
        # Test detailed health check
        response = client.get("/health/?detailed=true")
        assert response.status_code == 200

        data = response.json()
        assert data["phase"] == "1"
        assert "components" in data
        assert "summary" in data

        # Verify component structure
        components = data["components"]
        assert len(components) > 0

        for component in components:
            assert "name" in component
            assert "status" in component
            assert "message" in component
            assert "last_check" in component

        # Verify summary structure
        summary = data["summary"]
        assert "healthy" in summary
        assert "degraded" in summary
        assert "unhealthy" in summary
        assert "unknown" in summary

        # Verify total components match summary
        total_in_summary = sum(summary.values())
        assert total_in_summary == len(components)
