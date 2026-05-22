# Test Coverage Plan

This plan establishes a comprehensive test suite to ensure code changes don't break existing functionality, focusing on regression testing for the translation system.

## Overview

Set up pytest-based integration tests for critical translation system functionality to catch regressions when code changes are made.

## Test Setup

### 1. Mock-Based Testing
- No database required
- Use pytest-mock for mocking database sessions
- Mock database queries and model instances
- Test business logic in isolation

### 2. Test Fixtures (tests/conftest.py)
- `mock_db_session` - Mock async database session
- `mock_language` - Mock PepsiLanguage instance
- `mock_translation` - Mock PepsiTranslation instance
- `mock_version_history` - Mock PepsiTranslationVersion instance
- `mock_feedback_correction` - Mock PepsiFeedbackCorrection instance

## Test Files to Create

### tests/test_version_history.py
**Test automatic version history creation:**
- Test version history created on translation create (with created_by)
- Test version history created on translation update
- Test version history created on approve
- Test version history created on reject
- Test version column points to latest version
- Test version history not created for no-op updates

### tests/test_approve_reject.py
**Test approve/reject functionality:**
- Test approve single translation by ID
- Test bulk approve by label
- Test approve sets status to APPROVED
- Test approve updates updated_by
- Test reject with corrected_value
- Test reject creates feedback correction
- Test reject sets status to REJECTED
- Test performed_by field consolidation

### tests/test_rollback.py
**Test rollback functionality:**
- Test rollback to specific version
- Test rollback creates new version history entry
- Test rollback updates version column
- Test rollback restores translation value
- Test rollback restores status
- Test rollback with invalid version_id

### tests/test_language_validation.py
**Test language code validation:**
- Test valid language codes pass validation
- Test invalid language codes raise ValueError
- Test validation error message includes list of valid codes
- Test validation called in ai_translate (single)
- Test validation called in ai_translate (batch)

### tests/test_feedback_corrections.py
**Test feedback corrections:**
- Test get_feedback_corrections returns list
- Test get_feedback_corrections filters by language_code
- Test get_feedback_corrections limits results
- Test feedback correction stores ai_original_value
- Test feedback correction stores corrected_value
- Test feedback correction stores correction_reason

### tests/test_translation_crud.py
**Test basic CRUD operations:**
- Test create_translation with default status PENDING_REVIEW
- Test create_translation with explicit status
- Test update_translation updates fields
- Test update_translation updates status
- Test list_translations filters by status
- Test get_translation includes new fields

### tests/test_mcp_tools.py
**Test MCP tools (via direct function calls):**
- Test approve_translation MCP tool (single ID)
- Test approve_translation MCP tool (bulk by label)
- Test reject_translation MCP tool with corrected_value
- Test reject_translation MCP tool without corrected_value
- Test get_translation_history MCP tool
- Test get_feedback_corrections MCP tool
- Test rollback_translation MCP tool
- Test performed_by defaults to "system_user" in MCP tools

### tests/test_rest_api.py
**Test REST API endpoints:**
- Test POST /translations/ai-translate (sync mode)
- Test POST /translations/ai-translate (async mode)
- Test GET /batch-status/{batch_id}
- Test POST /translations/{id}/approve
- Test POST /translations/{id}/reject
- Test GET /translations/{id}/history
- Test GET /feedback-corrections
- Test POST /translations/{id}/rollback/{version_id}
- Test GET /translations with status filter

## Test Execution

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_version_history.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run only failed tests:
```bash
pytest tests/ --lf
```

## Implementation Order

1. Create tests/conftest.py with mock fixtures
2. Create tests/test_version_history.py
3. Create tests/test_approve_reject.py
4. Create tests/test_rollback.py
5. Create tests/test_language_validation.py
6. Create tests/test_feedback_corrections.py
7. Create tests/test_translation_crud.py
8. Create tests/test_mcp_tools.py
9. Create tests/test_rest_api.py
10. Add pytest configuration to pyproject.toml
11. Run all tests and verify they pass

## Configuration Updates

### pyproject.toml
Add pytest configuration:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

Add test dependencies to requirements.txt:
- pytest-asyncio (already present)
- pytest-cov
- pytest-mock

## Testing Approach

**Mock-based unit testing strategy:**

1. **Service layer tests** - Test business logic with mocked database
   - Mock database session with AsyncMock
   - Mock model instances (PepsiTranslation, PepsiLanguage, etc.)
   - Mock query results and execute() calls
   - Test logic without actual database

2. **REST API tests** - Test HTTP endpoints with TestClient + mocked service layer
   - FastAPI TestClient simulates HTTP requests
   - Mock service layer functions
   - Test request/response handling, status codes, schemas
   - Catches regressions in API layer

3. **MCP tool tests** - Test MCP tool functions with mocked database
   - Mock database session
   - Call MCP tool functions with test data
   - Test performed_by defaults, bulk operations
   - Catches regressions in MCP layer

**Coverage scope:**
- **New functionality:** 100% covered (version history, approve/reject, rollback, validation, MCP tools)
- **Critical paths:** All main workflows tested
- **Not covered:** Actual SQL execution, database constraints, transaction behavior

**Why this approach:**
- Tests run fast (no database connection)
- No database setup required
- Easy to identify which layer has issues
- Catches regressions in code changes
- Coverage report shows untested areas

## Benefits

- Regression testing catches breaking changes
- Tests document expected behavior
- Easy to run before/after code changes
- Coverage report shows untested code
- Isolated tests run quickly
