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

    async def test_find_node_by_text_single_mode(self, mock_figma_document):
        """Test find_node_by_text in single mode (backward compatibility)."""
        from services.figma_service import find_node_by_text
        from unittest.mock import patch

        with patch('services.figma_service.fetch_file_document', return_value=mock_figma_document):
            result = await find_node_by_text(screen_id="home", default_text="Easy Order")

            assert result is not None
            assert "figma_file_key" in result
            assert "figma_node_id" in result
            # Should return single result dict, not batch
            assert not isinstance(result.get("Easy Order"), dict)

    async def test_find_node_by_text_batch_mode_all_found(self, mock_figma_document):
        """Test find_node_by_text in batch mode with all texts found."""
        from services.figma_service import find_node_by_text
        from unittest.mock import patch

        with patch('services.figma_service.fetch_file_document', return_value=mock_figma_document):
            result = await find_node_by_text(
                screen_id="home",
                default_texts=["Easy Order", "Shop by Brands"]
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "Easy Order" in result
            assert "Shop by Brands" in result
            # Both should have figma_node_id (assuming they exist in mock)
            assert "figma_file_key" in result["Easy Order"]
            assert "figma_node_id" in result["Easy Order"]

    async def test_find_node_by_text_batch_mode_partial_match(self, mock_figma_document):
        """Test find_node_by_text in batch mode with partial matches."""
        from services.figma_service import find_node_by_text
        from unittest.mock import patch

        with patch('services.figma_service.fetch_file_document', return_value=mock_figma_document):
            result = await find_node_by_text(
                screen_id="home",
                default_texts=["Easy Order", "NonExistentLabel"]
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "Easy Order" in result
            assert "NonExistentLabel" in result
            # Non-existent should have null figma_node_id
            assert result["NonExistentLabel"]["figma_node_id"] is None

    async def test_find_node_by_text_batch_mode_empty_list(self):
        """Test find_node_by_text with empty texts list."""
        from services.figma_service import find_node_by_text

        result = await find_node_by_text(screen_id="home", default_texts=[])

        assert result is not None
        # Should return empty dict or error for no text provided
        assert result["figma_file_key"] is None
        assert result["figma_node_id"] is None

    async def test_find_node_by_text_no_config(self):
        """Test find_node_by_text with invalid screen_id."""
        from services.figma_service import find_node_by_text

        result = await find_node_by_text(screen_id="invalid_screen", default_text="Test")

        assert result is not None
        assert result["figma_file_key"] is None
        assert result["figma_node_id"] is None

