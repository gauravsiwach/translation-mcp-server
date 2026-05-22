"""Tests for basic CRUD operations."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestTranslationCRUD:
    """Test basic CRUD operations."""

    async def test_create_translation_with_default_status_pending_review(self, mock_db_session, mock_translation):
        """Test create_translation with default status PENDING_REVIEW."""
        from services.translation_service import create_translation

        # Track the created translation
        created_translation = None
        
        # First call returns None (no existing translation)
        # Second call returns the created translation (for version history)
        call_count = [0]
        def mock_scalar_one_or_none():
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # No existing translation
            else:
                return created_translation  # Return created translation for version history
        
        mock_db_session.execute.return_value.scalar_one_or_none = mock_scalar_one_or_none
        
        # Mock add to capture and assign ID to the translation
        def mock_add(obj):
            nonlocal created_translation
            obj.id = 1
            created_translation = obj
        mock_db_session.add = MagicMock(side_effect=mock_add)

        result = await create_translation(
            mock_db_session,
            translations=[{
                "label": "basket.total",
                "language_code": "en",
                "translation": "Total",
                "type": "ui"
            }]
        )

        assert result is not None
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    async def test_create_translation_with_explicit_status(self, mock_db_session, mock_translation):
        """Test create_translation with explicit status."""
        from services.translation_service import create_translation

        # Track the created translation
        created_translation = None
        
        # First call returns None, second returns created translation
        call_count = [0]
        def mock_scalar_one_or_none():
            call_count[0] += 1
            if call_count[0] == 1:
                return None
            else:
                return created_translation
        
        mock_db_session.execute.return_value.scalar_one_or_none = mock_scalar_one_or_none
        
        # Mock add to capture and assign ID
        def mock_add(obj):
            nonlocal created_translation
            obj.id = 1
            created_translation = obj
        mock_db_session.add = MagicMock(side_effect=mock_add)

        result = await create_translation(
            mock_db_session,
            translations=[{
                "label": "basket.total",
                "language_code": "en",
                "translation": "Total",
                "type": "ui",
                "status": "APPROVED"
            }]
        )

        assert result is not None
        assert mock_db_session.add.called

    async def test_update_translation_updates_fields(self, mock_db_session, mock_translation):
        """Test update_translation updates fields."""
        from services.translation_service import update_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.translation = "Updated translation"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await update_translation(
            mock_db_session,
            translation_id=1,
            translation="Updated translation"
        )

        assert result is not None
        assert result["translation"] == "Updated translation"
        assert mock_db_session.commit.called

    async def test_update_translation_updates_status(self, mock_db_session, mock_translation):
        """Test update_translation updates status."""
        from services.translation_service import update_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation
        
        async def mock_refresh(obj):
            obj.status = "APPROVED"
        mock_db_session.refresh.side_effect = mock_refresh

        result = await update_translation(
            mock_db_session,
            translation_id=1,
            status="APPROVED"
        )

        assert result is not None
        assert result["status"] == "APPROVED"

    async def test_list_translations_filters_by_status(self, mock_db_session, mock_translation):
        """Test list_translations filters by status."""
        from services.translation_service import list_translations

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_translation]

        result = await list_translations(mock_db_session, status="PENDING_REVIEW")

        assert isinstance(result, list)
        assert len(result) == 1
        assert mock_db_session.execute.called

    async def test_get_translation_includes_new_fields(self, mock_db_session, mock_translation):
        """Test get_translation includes new fields."""
        from services.translation_service import get_translation

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_translation

        result = await get_translation(mock_db_session, 1)

        assert result is not None
        assert result["status"] is not None
        assert result["created_by"] is not None
        assert result["updated_by"] is not None
