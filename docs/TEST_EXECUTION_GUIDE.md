# Test Execution Guide

## Setup

All test dependencies are already in `requirements.txt`:
- pytest==9.0.3
- pytest-asyncio==1.3.0
- pytest-cov==6.0.0
- pytest-mock==3.14.0

## Running Tests

### In Virtual Environment

```bash
# Activate venv
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services --cov=api --cov-report=html

# Run specific test file
pytest tests/test_version_history.py -v

# Run specific test
pytest tests/test_version_history.py::TestVersionHistory::test_version_history_created_on_translation_create_with_created_by -v
```

## Test Structure

### Created Test Files
- `tests/conftest.py` - Mock fixtures for DB sessions and models
- `tests/test_version_history.py` - Version history creation tests
- `tests/test_approve_reject.py` - Approve/reject functionality tests
- `tests/test_rollback.py` - Rollback functionality tests
- `tests/test_language_validation.py` - Language code validation tests
- `tests/test_feedback_corrections.py` - Feedback corrections tests
- `tests/test_translation_crud.py` - Basic CRUD tests
- `tests/test_mcp_tools.py` - MCP service function tests
- `tests/test_rest_api.py` - REST API endpoint tests

### Test Approach
- **Mock-based**: No database required
- **Async**: All tests use async/await
- **Isolated**: Each test is independent
- **Fast**: Runs in seconds

## Current Status

Tests are created and running. Some failures exist due to mock setup issues that need refinement:
- Mock coroutines need proper await handling
- Some service functions need updated signatures
- REST API tests need proper FastAPI TestClient setup

## Next Steps

1. Fix mock setup in failing tests
2. Ensure all mocks properly handle async operations
3. Add more edge case coverage
4. Run full test suite with coverage report
5. Document any gaps in coverage

## Coverage Goals

Target 80%+ coverage for:
- Translation service functions
- Feedback service functions
- API endpoints
- Version history management
- Language validation
- Approve/reject workflows
