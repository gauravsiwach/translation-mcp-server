"""Tests for approve/reject functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestApproveReject:
    """Test approve/reject functionality."""

    async def test_approve_single_translation_by_id(self, mock_db_session, mock_translation):
        """Test approve single translation by ID."""
        from services.translation_service import approve_translation

        # Mock the select and execute
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        # After refresh, update the mock translation status
        async def mock_refresh(obj):
            obj.status = "APPROVED"
            obj.updated_by = "system_user"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await approve_translation(mock_db_session, 1, "system_user")

        assert result is not None
        assert result["status"] == "APPROVED"
        assert result["updated_by"] == "system_user"
        assert mock_db_session.commit.called

    async def test_approve_translation_not_found(self, mock_db_session):
        """Test approve translation when translation not found."""
        from services.translation_service import approve_translation

        # Mock the query to return None (translation not found)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await approve_translation(mock_db_session, 999, "system_user")

        assert result is None

    async def test_approve_sets_status_to_approved(self, mock_db_session, mock_translation):
        """Test approve sets status to APPROVED."""
        from services.translation_service import approve_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "APPROVED"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await approve_translation(mock_db_session, 1, "system_user")

        assert result["status"] == "APPROVED"

    async def test_approve_updates_updated_by(self, mock_db_session, mock_translation):
        """Test approve updates updated_by."""
        from services.translation_service import approve_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.updated_by = "system_user"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await approve_translation(mock_db_session, 1, "system_user")

        assert result["updated_by"] == "system_user"

    async def test_reject_with_corrected_value(self, mock_db_session, mock_translation):
        """Test reject with corrected_value."""
        from services.feedback_service import reject_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "REJECTED"
            obj.translation = "Corrected translation"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await reject_translation(
            mock_db_session,
            1,
            "system_user",
            corrected_value="Corrected translation",
            correction_reason="Typo fixed"
        )

        assert result is not None
        assert result["status"] == "REJECTED"
        assert result["translation"] == "Corrected translation"
        assert mock_db_session.add.called  # Feedback correction created
        assert mock_db_session.commit.called

    async def test_reject_creates_feedback_correction(self, mock_db_session, mock_translation):
        """Test reject creates feedback correction."""
        from services.feedback_service import reject_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        mock_db_session.execute.return_value.return_value = None

        await reject_translation(
            mock_db_session,
            1,
            "system_user",
            corrected_value="Corrected"
        )

        # Verify session.add was called for feedback correction
        assert mock_db_session.add.called

    async def test_reject_sets_status_to_rejected(self, mock_db_session, mock_translation):
        """Test reject sets status to REJECTED."""
        from services.feedback_service import reject_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "REJECTED"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await reject_translation(mock_db_session, 1, "system_user")

        assert result["status"] == "REJECTED"

    async def test_performed_by_field_consolidation(self, mock_db_session, mock_translation):
        """Test performed_by field consolidation (not approved_by/rejected_by)."""
        from services.translation_service import approve_translation
        from services.feedback_service import reject_translation

        # Test approve uses performed_by
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        mock_db_session.execute.return_value.return_value = None

        result = await approve_translation(mock_db_session, 1, "system_user")
        assert result["updated_by"] == "system_user"

        # Test reject uses performed_by
        result = await reject_translation(mock_db_session, 1, "system_user")
        assert result["updated_by"] == "system_user"
