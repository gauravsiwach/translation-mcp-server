"""Pytest configuration and fixtures for mock-based testing."""
import sys
from pathlib import Path

# Add src directory to Python path (service files import from db, services without src prefix)
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    
    # Mock execute to return an awaitable result
    execute_result = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    
    # Mock scalar_one_or_none to return None by default
    execute_result.scalar_one_or_none = MagicMock(return_value=None)
    execute_result.scalar_one = MagicMock(return_value=1)
    
    # Mock scalars().all() chain
    scalars_result = MagicMock()
    scalars_result.all = MagicMock(return_value=[])
    execute_result.scalars = MagicMock(return_value=scalars_result)
    
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_language():
    """Mock PepsiLanguage instance."""
    language = MagicMock()
    language.language_code = "en"
    language.language = "English"
    language.created_datetime = datetime.now()
    language.updated_datetime = datetime.now()
    return language


@pytest.fixture
def mock_translation():
    """Mock PepsiTranslation instance."""
    translation = MagicMock()
    translation.id = 1
    translation.label = "basket.total"
    translation.language_code = "en"
    translation.translation = "Total"
    translation.type = "ui"
    translation.status = "PENDING_REVIEW"
    translation.figma_node_id = None
    translation.figma_file_key = None
    translation.figma_screenshot_url = None
    translation.created_by = "system_user"
    translation.updated_by = "system_user"
    translation.created_datetime = datetime.now()
    translation.updated_datetime = datetime.now()
    translation.version = None
    return translation


@pytest.fixture
def mock_version_history():
    """Mock PepsiTranslationVersion instance."""
    version = MagicMock()
    version.id = 1
    version.translation_id = 1
    version.label = "basket.total"
    version.translation = "Total"
    version.type = "ui"
    version.status = "APPROVED"
    version.changed_by = "system_user"
    version.change_reason = "Status changed to APPROVED"
    version.created_at = datetime.now()
    return version


@pytest.fixture
def mock_feedback_correction():
    """Mock PepsiFeedbackCorrection instance."""
    correction = MagicMock()
    correction.id = 1
    correction.translation_id = 1
    correction.label = "basket.total"
    correction.language_code = "hi"
    correction.ai_original_value = "टोटल"
    correction.corrected_value = "कुल"
    correction.correction_reason = "More accurate"
    correction.corrected_by = "system_user"
    correction.created_at = datetime.now()
    return correction
