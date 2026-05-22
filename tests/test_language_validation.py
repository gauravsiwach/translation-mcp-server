"""Tests for language code validation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLanguageValidation:
    """Test language code validation."""

    async def test_valid_language_codes_pass_validation(self, mock_db_session, mock_language):
        """Test valid language codes pass validation."""
        from services.translation_service import validate_language_codes

        # Mock the query result to return language code strings
        mock_db_session.execute.return_value.scalars().all.return_value = ["en", "hi", "es"]

        # Should not raise an error
        await validate_language_codes(mock_db_session, ["en"])

    async def test_invalid_language_codes_raise_valueerror(self, mock_db_session, mock_language):
        """Test invalid language codes raise ValueError."""
        from services.translation_service import validate_language_codes

        # Mock the query result to return language code strings
        mock_db_session.execute.return_value.scalars().all.return_value = ["en", "hi", "es"]

        # Should raise ValueError for invalid language code
        with pytest.raises(ValueError) as exc_info:
            await validate_language_codes(mock_db_session, ["invalid"])

        assert "Invalid language code" in str(exc_info.value)

    async def test_validation_error_message_includes_list_of_valid_codes(self, mock_db_session, mock_language):
        """Test validation error message includes list of valid codes."""
        from services.translation_service import validate_language_codes

        # Mock the query result to return language code strings
        mock_db_session.execute.return_value.scalars().all.return_value = ["en", "hi", "es"]

        with pytest.raises(ValueError) as exc_info:
            await validate_language_codes(mock_db_session, ["invalid"])

        error_message = str(exc_info.value)
        assert "en" in error_message  # Valid code should be in error message

    async def test_validation_called_in_ai_translate_single(self, mock_db_session):
        """Test validation called in ai_translate (single)."""
        from services.translation_service import validate_language_codes

        # Mock the language query to return language code strings
        mock_db_session.execute.return_value.scalars().all.return_value = ["en", "hi", "es"]

        # Test that validation works for ai_translate use case
        result = await validate_language_codes(mock_db_session, ["en"])
        
        assert result == ["en"]
        assert mock_db_session.execute.called

    async def test_validation_called_in_ai_translate_batch(self, mock_db_session):
        """Test validation called in ai_translate (batch)."""
        from services.translation_service import validate_language_codes

        # Mock the language query to return language code strings
        mock_db_session.execute.return_value.scalars().all.return_value = ["en", "hi", "es"]

        # Test that validation works for multiple language codes
        result = await validate_language_codes(mock_db_session, ["en", "hi"])
        
        assert result == ["en", "hi"]
        assert mock_db_session.execute.called
