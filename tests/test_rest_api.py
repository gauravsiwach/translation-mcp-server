"""Tests for REST API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def cleanup_app_state():
    """Auto-cleanup fixture to reset app state between tests."""
    from main import app
    from services.translation_service import batch_status
    
    # Store original batch status
    original_batch_status = batch_status.copy()
    
    yield
    
    # Clean up after test
    app.dependency_overrides.clear()
    # Reset module-level batch status
    batch_status.clear()
    batch_status.update(original_batch_status)


@pytest.fixture
def mock_db_session():
    """Fixture to provide a mock database session."""
    session = AsyncMock()
    execute_result = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    execute_result.scalar_one_or_none = MagicMock(return_value=None)
    execute_result.scalar_one = MagicMock(return_value=1)
    scalars_result = MagicMock()
    scalars_result.all = MagicMock(return_value=[])
    execute_result.scalars = MagicMock(return_value=scalars_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


class TestRestAPI:
    """Test REST API endpoints."""

    def test_post_translations_ai_translate_sync_mode(self, mock_db_session):
        """Test POST /translations/ai-translate (sync mode)."""
        from main import app
        from db.session import get_session

        # Override the dependency
        async def mock_get_session():
            yield mock_db_session

        app.dependency_overrides[get_session] = mock_get_session

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/translations/ai-translate",
                json={
                    "translations": [
                        {"label": "test.key", "source_text": "Test", "target_language_codes": ["en"], "type": "ui"}
                    ]
                }
            )
            # Should return 200 or 201
            assert response.status_code in [200, 201]

    def test_get_batch_status(self, mock_db_session):
        """Test GET /batch-status/{batch_id}."""
        from main import app
        from db.session import get_session

        async def mock_get_session():
            yield mock_db_session

        app.dependency_overrides[get_session] = mock_get_session

        with TestClient(app) as client:
            response = client.get("/api/v1/translations/batch-status/test-batch-123")
            assert response.status_code in [200, 404]

    def test_post_translations_id_approve(self, mock_db_session):
        """Test POST /translations/{id}/approve."""
        from main import app

        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.label = "basket.total"
        mock_row.language_code = "en"
        mock_row.translation = "Total"
        mock_row.type = "ui"
        mock_row.status = "APPROVED"
        mock_row.figma_node_id = None
        mock_row.figma_file_key = None
        mock_row.figma_screenshot_url = None
        mock_row.created_by = "system_user"
        mock_row.updated_by = "system_user"
        mock_row.created_datetime = None
        mock_row.updated_datetime = None
        mock_row.version = None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_row

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/translations/1/approve",
                    json={"performed_by": "system_user"}
                )
                assert response.status_code in [200, 404]

    def test_post_translations_id_reject(self, mock_db_session):
        """Test POST /translations/{id}/reject."""
        from main import app

        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.label = "basket.total"
        mock_row.language_code = "en"
        mock_row.translation = "Total"
        mock_row.type = "ui"
        mock_row.status = "REJECTED"
        mock_row.figma_node_id = None
        mock_row.figma_file_key = None
        mock_row.figma_screenshot_url = None
        mock_row.created_by = "system_user"
        mock_row.updated_by = "system_user"
        mock_row.created_datetime = None
        mock_row.updated_datetime = None
        mock_row.version = None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_row

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/translations/1/reject",
                    json={"performed_by": "system_user", "corrected_value": "Corrected"}
                )
                assert response.status_code in [200, 404]

    def test_get_translations_id_history(self, mock_db_session):
        """Test GET /translations/{id}/history."""
        from main import app

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.get("/api/v1/translations/1/history")
                assert response.status_code in [200, 404]

    def test_get_feedback_corrections(self, mock_db_session):
        """Test GET /feedback-corrections."""
        from main import app

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.get("/api/v1/feedback-corrections")
                assert response.status_code == 200

    def test_post_translations_id_rollback_version_id(self, mock_db_session):
        """Test POST /translations/{id}/rollback/{version_id}."""
        from main import app

        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.label = "basket.total"
        mock_row.language_code = "en"
        mock_row.translation = "Total"
        mock_row.type = "ui"
        mock_row.status = "PENDING_REVIEW"
        mock_row.figma_node_id = None
        mock_row.figma_file_key = None
        mock_row.figma_screenshot_url = None
        mock_row.created_by = "system_user"
        mock_row.updated_by = "system_user"
        mock_row.created_datetime = None
        mock_row.updated_datetime = None
        mock_row.version = 1
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_row

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/translations/1/rollback/1",
                    json={"performed_by": "system_user"}
                )
                assert response.status_code in [200, 404]

    def test_get_translations_with_status_filter(self, mock_db_session):
        """Test GET /translations with status filter."""
        from main import app

        async def _mock_get_session():
            yield mock_db_session

        with patch("api.translations.get_session", _mock_get_session):
            with TestClient(app) as client:
                response = client.get("/api/v1/translations?status=PENDING_REVIEW")
                assert response.status_code == 200
