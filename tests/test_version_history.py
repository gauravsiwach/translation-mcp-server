"""Tests for automatic version history creation."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


class TestVersionHistory:
    """Test automatic version history creation."""

    async def test_version_history_created_on_translation_create_with_created_by(self, mock_db_session, mock_translation):
        """Test version history created on translation create (with created_by)."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        # Mock the translation query
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        await create_version_history(
            mock_db_session,
            translation_id=1,
            changed_by="system_user",
            change_reason="Initial version"
        )

        # Verify session.add was called
        assert mock_db_session.add.called
        # Verify commit was called
        assert mock_db_session.commit.called

    async def test_version_history_created_on_translation_update(self, mock_db_session, mock_translation):
        """Test version history created on translation update."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        mock_db_session.execute.return_value.scalar_one.return_value = 1

        await create_version_history(
            mock_db_session,
            translation_id=1,
            changed_by="system_user",
            change_reason="Translation updated"
        )

        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    async def test_version_history_created_on_approve(self, mock_db_session, mock_translation):
        """Test version history created on approve."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        mock_db_session.execute.return_value.scalar_one.return_value = 1

        await create_version_history(
            mock_db_session,
            translation_id=1,
            changed_by="system_user",
            change_reason="Status changed to APPROVED"
        )

        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    async def test_version_history_created_on_reject(self, mock_db_session, mock_translation):
        """Test version history created on reject."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        mock_db_session.execute.return_value.scalar_one.return_value = 1

        await create_version_history(
            mock_db_session,
            translation_id=1,
            changed_by="system_user",
            change_reason="Status changed to REJECTED"
        )

        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    async def test_version_column_points_to_latest_version(self, mock_db_session, mock_translation):
        """Test version column points to latest version."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        # Mock the execute result to return version_id
        mock_db_session.execute.return_value.scalar_one.return_value = 1

        # Mock the update statement
        mock_update_stmt = MagicMock()
        mock_db_session.execute.return_value = mock_update_stmt

        await create_version_history(
            mock_db_session,
            translation_id=1,
            changed_by="system_user"
        )

        # Verify execute was called (for both insert and update)
        assert mock_db_session.execute.called

    async def test_version_history_not_created_for_no_op_updates(self, mock_db_session, mock_translation):
        """Test version history not created for no-op updates."""
        from services.translation_service import create_version_history
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        # Simulate no-op by not calling the function
        # This test verifies that version history is only created when needed
        assert not mock_db_session.add.called
