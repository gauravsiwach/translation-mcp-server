"""Tests for rollback functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestRollback:
    """Test rollback functionality."""

    async def test_rollback_to_specific_version(self, mock_db_session, mock_version_history):
        """Test rollback to specific version."""
        from services.translation_service import rollback_translation

        # Mock the version history query
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_version_history
        mock_db_session.execute.return_value.return_value = None

        result = await rollback_translation(
            mock_db_session,
            translation_id=1,
            version_id=1,
            performed_by="system_user"
        )

        assert result is not None
        assert mock_db_session.commit.called

    async def test_rollback_creates_new_version_history_entry(self, mock_db_session, mock_version_history):
        """Test rollback creates new version history entry."""
        from services.translation_service import rollback_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_version_history
        mock_db_session.execute.return_value.return_value = None

        await rollback_translation(mock_db_session, 1, 1, "system_user")

        # Verify session.add was called for new version history
        assert mock_db_session.add.called

    async def test_rollback_updates_version_column(self, mock_db_session, mock_version_history):
        """Test rollback updates version column."""
        from services.translation_service import rollback_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_version_history
        mock_db_session.execute.return_value.return_value = None

        await rollback_translation(mock_db_session, 1, 1, "system_user")

        # Verify execute was called for update
        assert mock_db_session.execute.called

    async def test_rollback_restores_translation_value(self, mock_db_session, mock_version_history):
        """Test rollback restores translation value."""
        from services.translation_service import rollback_translation

        mock_version_history.translation = "Old translation value"
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_version_history
        mock_db_session.execute.return_value.return_value = None

        result = await rollback_translation(mock_db_session, 1, 1, "system_user")

        assert result["translation"] == "Old translation value"

    async def test_rollback_restores_status(self, mock_db_session, mock_version_history):
        """Test rollback restores status."""
        from services.translation_service import rollback_translation

        mock_version_history.status = "APPROVED"
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_version_history
        mock_db_session.execute.return_value.return_value = None

        result = await rollback_translation(mock_db_session, 1, 1, "system_user")

        assert result["status"] == "APPROVED"

    async def test_rollback_with_invalid_version_id(self, mock_db_session):
        """Test rollback with invalid version_id."""
        from services.translation_service import rollback_translation

        # Mock version not found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await rollback_translation(mock_db_session, 1, 999, "system_user")

        assert result is None
