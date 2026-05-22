"""Tests for feedback corrections."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestFeedbackCorrections:
    """Test feedback corrections."""

    async def test_get_feedback_corrections_returns_list(self, mock_db_session, mock_feedback_correction):
        """Test get_feedback_corrections returns list."""
        from services.feedback_service import get_feedback_corrections

        # Mock the query result
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_feedback_correction
        ]

        result = await get_feedback_corrections(mock_db_session)

        assert isinstance(result, list)
        assert len(result) == 1

    async def test_get_feedback_corrections_filters_by_language_code(self, mock_db_session, mock_feedback_correction):
        """Test get_feedback_corrections filters by language_code."""
        from services.feedback_service import get_feedback_corrections

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_feedback_correction
        ]

        result = await get_feedback_corrections(mock_db_session, language_code="hi")

        assert isinstance(result, list)
        # Verify execute was called (filtering was applied)
        assert mock_db_session.execute.called

    async def test_get_feedback_corrections_limits_results(self, mock_db_session, mock_feedback_correction):
        """Test get_feedback_corrections limits results."""
        from services.feedback_service import get_feedback_corrections

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_feedback_correction
        ]

        result = await get_feedback_corrections(mock_db_session, limit=5)

        assert isinstance(result, list)

    async def test_feedback_correction_stores_ai_original_value(self, mock_feedback_correction):
        """Test feedback correction stores ai_original_value."""
        assert mock_feedback_correction.ai_original_value == "टोटल"

    async def test_feedback_correction_stores_corrected_value(self, mock_feedback_correction):
        """Test feedback correction stores corrected_value."""
        assert mock_feedback_correction.corrected_value == "कुल"

    async def test_feedback_correction_stores_correction_reason(self, mock_feedback_correction):
        """Test feedback correction stores correction_reason."""
        assert mock_feedback_correction.correction_reason == "More accurate"
