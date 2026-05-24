"""Tests for MCP tools (service functions that MCP tools call)."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestMCPTools:
    """Test MCP tools (via direct service function calls)."""

    async def test_approve_translation_service_function(self, mock_db_session, mock_translation):
        """Test approve_translation service function (called by MCP tool)."""
        from services.translation_service import approve_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "APPROVED"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await approve_translation(mock_db_session, 1, "system_user")

        assert result is not None
        assert result["status"] == "APPROVED"

    async def test_reject_translation_service_function(self, mock_db_session, mock_translation):
        """Test reject_translation service function (called by MCP tool)."""
        from services.feedback_service import reject_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "REJECTED"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await reject_translation(
            mock_db_session,
            1,
            "system_user",
            corrected_value="Corrected",
            correction_reason="Fix"
        )

        assert result is not None
        assert result["status"] == "REJECTED"

    async def test_get_feedback_corrections_service_function(self, mock_db_session, mock_feedback_correction):
        """Test get_feedback_corrections service function (called by MCP tool)."""
        from services.feedback_service import get_feedback_corrections

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_feedback_correction]

        result = await get_feedback_corrections(mock_db_session)

        assert isinstance(result, list)

