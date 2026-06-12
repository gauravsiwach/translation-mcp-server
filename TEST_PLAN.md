# Translation MCP Server - Comprehensive Test Plan

## Overview
This test plan covers all REST API endpoints and MCP tools for the Translation MCP Server, including the new batch Figma search optimization.

## Test Environment Setup
- MCP Server running on configured port
- Database with test data (seeded languages, sample translations)
- Figma API access configured with valid credentials
- Test screen configurations in `figma_screens.json`

---

## REST API Tests

### 1. Languages Endpoints

#### 1.1 GET /languages
**Purpose:** Retrieve all available languages

**Test Cases:**
- TC-LANG-001: Get all languages (success)
  - Expected: Array of language objects with language_code, language, timestamps
- TC-LANG-002: Empty database
  - Expected: Empty array

**Example:**
```bash
curl -X GET http://localhost:8000/languages
```

**Expected Response:**
```json
[
  {
    "language_code": "en",
    "language": "English",
    "created_datetime": "2024-01-01T00:00:00",
    "updated_datetime": "2024-01-01T00:00:00"
  },
  {
    "language_code": "hi_IND",
    "language": "Hindi (India)",
    "created_datetime": "2024-01-01T00:00:00",
    "updated_datetime": "2024-01-01T00:00:00"
  }
]
```

---

### 2. Translations Endpoints

#### 2.1 GET /translations
**Purpose:** Retrieve translations with optional filters

**Test Cases:**
- TC-TRANS-001: Get all translations (no filters)
- TC-TRANS-002: Filter by language_code
- TC-TRANS-003: Filter by label
- TC-TRANS-004: Filter by type
- TC-TRANS-005: Multiple filters combined
- TC-TRANS-006: No matching results
- TC-TRANS-007: Invalid language_code

**Examples:**

```bash
# Get all translations
curl -X GET http://localhost:8000/translations

# Filter by language
curl -X GET http://localhost:8000/translations?language_code=en

# Filter by label
curl -X GET http://localhost:8000/translations?label=home.easy_order

# Filter by type
curl -X GET http://localhost:8000/translations?type=ui

# Multiple filters
curl -X GET http://localhost:8000/translations?language_code=en&label=home.easy_order
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "label": "home.easy_order",
    "language_code": "en",
    "translation": "Easy Order",
    "type": "ui",
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": "35773:133679",
    "figma_screenshot_url": "https://cdn.figma.com/...",
    "status": "PENDING",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### 2.2 POST /translations
**Purpose:** Create or update translations (bulk upsert)

**Test Cases:**
- TC-TRANS-008: Create new translation (single)
- TC-TRANS-009: Create new translations (bulk)
- TC-TRANS-010: Update existing translation
- TC-TRANS-011: Mixed create and update
- TC-TRANS-012: Missing required fields
- TC-TRANS-013: Invalid language_code
- TC-TRANS-014: Empty array

**Example:**
```bash
curl -X POST http://localhost:8000/translations \
  -H "Content-Type: application/json" \
  -d '[
    {
      "label": "home.easy_order",
      "language_code": "en",
      "translation": "Easy Order",
      "type": "ui"
    },
    {
      "label": "home.easy_order",
      "language_code": "hi_IND",
      "translation": "आसान ऑर्डर",
      "type": "ui"
    }
  ]'
```

**Expected Response:**
```json
{
  "total": 2,
  "created": 2,
  "updated": 0,
  "results": [
    {
      "id": 1,
      "label": "home.easy_order",
      "language_code": "en",
      "translation": "Easy Order",
      "type": "ui",
      "status": "PENDING"
    },
    {
      "id": 2,
      "label": "home.easy_order",
      "language_code": "hi_IND",
      "translation": "आसान ऑर्डर",
      "type": "ui",
      "status": "PENDING"
    }
  ]
}
```

#### 2.3 PUT /translations/{id}
**Purpose:** Update a specific translation by ID

**Test Cases:**
- TC-TRANS-015: Update translation text
- TC-TRANS-016: Update translation type
- TC-TRANS-017: Update both text and type
- TC-TRANS-018: Invalid translation ID
- TC-TRANS-019: Update with empty text

**Example:**
```bash
curl -X PUT http://localhost:8000/translations/1 \
  -H "Content-Type: application/json" \
  -d '{
    "translation": "Quick Order",
    "type": "ui"
  }'
```

#### 2.4 PUT /translations/by-key
**Purpose:** Update translation by label + language_code

**Test Cases:**
- TC-TRANS-020: Update by valid key
- TC-TRANS-021: Invalid label
- TC-TRANS-022: Invalid language_code
- TC-TRANS-023: Key combination not found

**Example:**
```bash
curl -X PUT http://localhost:8000/translations/by-key \
  -H "Content-Type: application/json" \
  -d '{
    "label": "home.easy_order",
    "language_code": "en",
    "translation": "Quick Order"
  }'
```

---

### 3. AI Translation Endpoints

#### 3.1 POST /translations/ai-translate
**Purpose:** Bulk AI translate labels to target languages

**Test Cases:**
- TC-AI-001: Single translation (sync mode, ≤10 items)
- TC-AI-002: Bulk translations (sync mode, ≤10 items)
- TC-AI-003: Bulk translations (async mode, >10 items)
- TC-AI-004: Missing source_text
- TC-AI-005: Missing target_language_codes
- TC-AI-006: Invalid language_code
- TC-AI-007: Empty array

**Example (Sync Mode):**
```bash
curl -X POST http://localhost:8000/translations/ai-translate \
  -H "Content-Type: application/json" \
  -d '[
    {
      "label": "home.easy_order",
      "source_text": "Easy Order",
      "target_language_codes": ["hi_IND", "es_ES"],
      "type": "ui"
    }
  ]'
```

**Expected Response (Sync):**
```json
{
  "mode": "sync",
  "total_requested": 1,
  "upserted": 2,
  "total": 2
}
```

**Expected Response (Async):**
```json
{
  "mode": "async",
  "batch_id": "batch-abc-123",
  "total_requested": 15,
  "status": "processing"
}
```

#### 3.2 GET /translations/batch/{batch_id}
**Purpose:** Check async batch status

**Test Cases:**
- TC-AI-008: Valid batch_id (processing)
- TC-AI-009: Valid batch_id (completed)
- TC-AI-010: Valid batch_id (failed)
- TC-AI-011: Invalid batch_id

**Example:**
```bash
curl -X GET http://localhost:8000/translations/batch/batch-abc-123
```

**Expected Response:**
```json
{
  "batch_id": "batch-abc-123",
  "status": "completed",
  "total": 15,
  "completed": 15,
  "pending": 0,
  "failed": 0,
  "results": [...]
}
```

---

### 4. Download Endpoints

#### 4.1 GET /translations/download
**Purpose:** Download all translations as CSV or JSON

**Test Cases:**
- TC-DOWN-001: Download as CSV
- TC-DOWN-002: Download as JSON
- TC-DOWN-003: Invalid format
- TC-DOWN-004: Empty database

**Example:**
```bash
# Download as CSV
curl -X GET http://localhost:8000/translations/download?format=csv \
  -o translations.csv

# Download as JSON
curl -X GET http://localhost:8000/translations/download?format=json \
  -o translations.json
```

#### 4.2 GET /translations/batch/{batch_id}/download
**Purpose:** Download completed batch results

**Test Cases:**
- TC-DOWN-005: Download completed batch (CSV)
- TC-DOWN-006: Download completed batch (JSON)
- TC-DOWN-007: Download processing batch
- TC-DOWN-008: Invalid batch_id

**Example:**
```bash
curl -X GET http://localhost:8000/translations/batch/batch-abc-123/download?format=csv \
  -o batch_results.csv
```

---

### 5. Approval/Rejection Endpoints

#### 5.1 POST /translations/{id}/approve
**Purpose:** Approve a translation

**Test Cases:**
- TC-APPR-001: Approve valid translation
- TC-APPR-002: Approve already approved translation
- TC-APPR-003: Invalid translation ID
- TC-APPR-004: Bulk approve by label

**Example:**
```bash
curl -X POST http://localhost:8000/translations/1/approve \
  -H "Content-Type: application/json" \
  -d '{"performed_by": "test_user"}'
```

#### 5.2 POST /translations/{id}/reject
**Purpose:** Reject a translation with optional correction

**Test Cases:**
- TC-REJ-001: Reject without correction
- TC-REJ-002: Reject with correction
- TC-REJ-003: Reject with reason
- TC-REJ-004: Invalid translation ID

**Example:**
```bash
curl -X POST http://localhost:8000/translations/1/reject \
  -H "Content-Type: application/json" \
  -d '{
    "performed_by": "test_user",
    "corrected_value": "Better Translation",
    "correction_reason": "More accurate translation"
  }'
```

#### 5.3 GET /feedback/corrections
**Purpose:** Get recent feedback corrections

**Test Cases:**
- TC-FEED-001: Get all corrections
- TC-FEED-002: Filter by language_code
- TC-FEED-003: Limit results
- TC-FEED-004: No corrections found

**Example:**
```bash
curl -X GET http://localhost:8000/feedback/corrections?language_code=hi_IND&limit=10
```

---

## MCP Tools Tests

### 1. list_languages
**Purpose:** Get all available languages via MCP

**Test Cases:**
- TC-MCP-LANG-001: List all languages
- TC-MCP-LANG-002: Empty database

**Example Call:**
```python
result = await mcp.call_tool("list_languages")
```

**Expected Result:**
```json
[
  {"language_code": "en", "language": "English"},
  {"language_code": "hi_IND", "language": "Hindi (India)"}
]
```

---

### 2. get_translations
**Purpose:** Filter translations via MCP

**Test Cases:**
- TC-MCP-TRANS-001: Get all translations
- TC-MCP-TRANS-002: Filter by language_code
- TC-MCP-TRANS-003: Filter by label
- TC-MCP-TRANS-004: Filter by type
- TC-MCP-TRANS-005: No matching results

**Example Call:**
```python
result = await mcp.call_tool("get_translations", {
  "language_code": "en",
  "label": "home.easy_order"
})
```

---

### 3. create_translation
**Purpose:** Bulk upsert translations via MCP

**Test Cases:**
- TC-MCP-CREATE-001: Create single translation
- TC-MCP-CREATE-002: Create bulk translations
- TC-MCP-CREATE-003: Update existing translation
- TC-MCP-CREATE-004: Missing required fields
- TC-MCP-CREATE-005: Empty array

**Example Call:**
```python
result = await mcp.call_tool("create_translation", {
  "translations": [
    {
      "label": "home.easy_order",
      "language_code": "en",
      "translation": "Easy Order",
      "type": "ui"
    }
  ]
})
```

---

### 4. update_translation
**Purpose:** Update translation via MCP

**Test Cases:**
- TC-MCP-UPDATE-001: Update by ID
- TC-MCP-UPDATE-002: Update by label + language_code
- TC-MCP-UPDATE-003: Invalid ID
- TC-MCP-UPDATE-004: Invalid key combination

**Example Call (by ID):**
```python
result = await mcp.call_tool("update_translation", {
  "translation_id": 1,
  "translation": "Quick Order",
  "type": "ui"
})
```

**Example Call (by key):**
```python
result = await mcp.call_tool("update_translation", {
  "label": "home.easy_order",
  "language_code": "en",
  "translation": "Quick Order"
})
```

---

### 5. ai_translate
**Purpose:** Bulk AI translate via MCP

**Test Cases:**
- TC-MCP-AI-001: Single translation (sync)
- TC-MCP-AI-002: Bulk translations (sync)
- TC-MCP-AI-003: Bulk translations (async)
- TC-MCP-AI-004: Missing source_text

**Example Call:**
```python
result = await mcp.call_tool("ai_translate", {
  "translations": [
    {
      "label": "home.easy_order",
      "source_text": "Easy Order",
      "target_language_codes": ["hi_IND", "es_ES"],
      "type": "ui"
    }
  ]
})
```

---

### 6. get_batch_status
**Purpose:** Check async batch status via MCP

**Test Cases:**
- TC-MCP-BATCH-001: Valid batch_id
- TC-MCP-BATCH-002: Invalid batch_id

**Example Call:**
```python
result = await mcp.call_tool("get_batch_status", {
  "batch_id": "batch-abc-123"
})
```

---

### 7. download_translations
**Purpose:** Download translations via MCP

**Test Cases:**
- TC-MCP-DOWN-001: Download as CSV
- TC-MCP-DOWN-002: Download as JSON
- TC-MCP-DOWN-003: Invalid format

**Example Call:**
```python
result = await mcp.call_tool("download_translations", {
  "format": "csv"
})
```

---

### 8. approve_translation
**Purpose:** Approve translation via MCP

**Test Cases:**
- TC-MCP-APPR-001: Approve by ID
- TC-MCP-APPR-002: Bulk approve by label
- TC-MCP-APPR-003: Invalid ID

**Example Call (single):**
```python
result = await mcp.call_tool("approve_translation", {
  "translation_id": 1,
  "performed_by": "test_user"
})
```

**Example Call (bulk):**
```python
result = await mcp.call_tool("approve_translation", {
  "label": "home.easy_order",
  "performed_by": "test_user"
})
```

---

### 9. reject_translation
**Purpose:** Reject translation via MCP

**Test Cases:**
- TC-MCP-REJ-001: Reject without correction
- TC-MCP-REJ-002: Reject with correction
- TC-MCP-REJ-003: Invalid ID

**Example Call:**
```python
result = await mcp.call_tool("reject_translation", {
  "translation_id": 1,
  "performed_by": "test_user",
  "corrected_value": "Better Translation",
  "correction_reason": "More accurate"
})
```

---

### 10. get_feedback_corrections
**Purpose:** Get feedback corrections via MCP

**Test Cases:**
- TC-MCP-FEED-001: Get all corrections
- TC-MCP-FEED-002: Filter by language_code
- TC-MCP-FEED-003: Limit results

**Example Call:**
```python
result = await mcp.call_tool("get_feedback_corrections", {
  "language_code": "hi_IND",
  "limit": 10
})
```

---

## Figma Integration Tests

### 11. get_figma_screenshot_url
**Purpose:** Fetch screenshot URL for Figma node

**Test Cases:**
- TC-FIGMA-001: Valid file_key and node_id
- TC-FIGMA-002: Invalid file_key
- TC-FIGMA-003: Invalid node_id

**Example Call:**
```python
result = await mcp.call_tool("get_figma_screenshot_url", {
  "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
  "figma_node_id": "35773:133679"
})
```

**Expected Result:**
```json
{
  "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
  "figma_node_id": "35773:133679",
  "screenshot_url": "https://cdn.figma.com/..."
}
```

---

### 12. find_figma_node_by_text (Single Mode)
**Purpose:** Find single Figma node by text

**Test Cases:**
- TC-FIGMA-004: Valid screen_id and exact match
- TC-FIGMA-005: Valid screen_id, no match
- TC-FIGMA-006: Invalid screen_id
- TC-FIGMA-007: Instance ID (contains semicolon) - should be skipped

**Example Call:**
```python
result = await mcp.call_tool("find_figma_node_by_text", {
  "screen_id": "home",
  "default_text": "Easy Order"
})
```

**Expected Result (match found):**
```json
{
  "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
  "figma_node_id": "35773:133679"
}
```

**Expected Result (no match):**
```json
{
  "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
  "figma_node_id": null
}
```

---

### 13. find_figma_node_by_text (Batch Mode) - NEW
**Purpose:** Find multiple Figma nodes on same screen (optimized)

**Test Cases:**
- TC-FIGMA-BATCH-001: Valid screen_id, multiple texts, all found
- TC-FIGMA-BATCH-002: Valid screen_id, multiple texts, partial match
- TC-FIGMA-BATCH-003: Valid screen_id, multiple texts, no matches
- TC-FIGMA-BATCH-004: Valid screen_id, single text in batch (should work)
- TC-FIGMA-BATCH-005: Invalid screen_id
- TC-FIGMA-BATCH-006: Empty texts array
- TC-FIGMA-BATCH-007: Mixed instance IDs and regular IDs
- TC-FIGMA-BATCH-008: Case-insensitive matching
- TC-FIGMA-BATCH-009: Whitespace trimming

**Example Call:**
```python
result = await mcp.call_tool("find_figma_node_by_text", {
  "screen_id": "home",
  "default_texts": ["Easy Order", "Shop by Brands"]
})
```

**Expected Result (all found):**
```json
{
  "Easy Order": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": "35773:133679"
  },
  "Shop by Brands": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": "I35773:133684;31011:251158"
  }
}
```

**Expected Result (partial match):**
```json
{
  "Easy Order": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": "35773:133679"
  },
  "NonExistent": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": null
  }
}
```

**Expected Result (no matches):**
```json
{
  "NonExistent1": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": null
  },
  "NonExistent2": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_node_id": null
  }
}
```

---

### 14. get_figma_screen_config
**Purpose:** Get Figma screen configuration

**Test Cases:**
- TC-FIGMA-CONFIG-001: Get specific screen config
- TC-FIGMA-CONFIG-002: Get all screen configs (no screen_id)
- TC-FIGMA-CONFIG-003: Invalid screen_id

**Example Call (specific):**
```python
result = await mcp.call_tool("get_figma_screen_config", {
  "screen_id": "home"
})
```

**Example Call (all):**
```python
result = await mcp.call_tool("get_figma_screen_config")
```

---

## Batch Figma Search Integration Tests

### 15. End-to-End Workflow Test
**Purpose:** Test complete batch Figma search workflow in translation creation

**Test Case:** TC-E2E-001

**Steps:**
1. User provides multiple labels from same screen: `home.easy_order`, `home.shop_by_brands`
2. System groups labels by screen_id: `home` (2 items)
3. System calls `find_figma_node_by_text` with batch mode
4. System processes results and shows screenshots
5. User confirms matches
6. System creates translations with Figma metadata

**Expected Result:**
- Single Figma API call for both labels
- Both translations created with correct Figma metadata
- Screenshots displayed for confirmation

---

## Edge Cases and Error Scenarios

### Database Errors
- TC-ERR-001: Database connection failure
- TC-ERR-002: Database timeout
- TC-ERR-003: Constraint violation

### Figma API Errors
- TC-ERR-004: Figma API rate limit exceeded
- TC-ERR-005: Figma API authentication failure
- TC-ERR-006: Figma file not found
- TC-ERR-007: Figma node not found
- TC-ERR-008: Figma API timeout

### AI Translation Errors
- TC-ERR-009: AI API quota exceeded
- TC-ERR-010: AI API timeout
- TC-ERR-011: Invalid language code for AI

### MCP Tool Errors
- TC-ERR-012: Missing required parameters
- TC-ERR-013: Invalid parameter types
- TC-ERR-014: Parameter validation failure

### Concurrent Operations
- TC-ERR-015: Simultaneous updates to same translation
- TC-ERR-016: Concurrent batch operations
- TC-ERR-017: Race conditions in approval workflow

---

## Performance Tests

### Batch Performance
- TC-PERF-001: Batch search with 5 texts on same screen
- TC-PERF-002: Batch search with 10 texts on same screen
- TC-PERF-003: Batch search with 20 texts on same screen
- TC-PERF-004: Compare batch vs individual API calls (measure time difference)

### Load Testing
- TC-PERF-005: 100 concurrent translation creations
- TC-PERF-006: 50 concurrent AI translation requests
- TC-PERF-007: 100 concurrent Figma node searches

---

## Security Tests

### Input Validation
- TC-SEC-001: SQL injection attempts
- TC-SEC-002: XSS attempts in translation text
- TC-SEC-003: Path traversal in file operations

### Authentication/Authorization
- TC-SEC-004: Unauthorized API access
- TC-SEC-005: Invalid API keys
- TC-SEC-006: Rate limiting enforcement

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] Database seeded with test data
- [ ] MCP server running
- [ ] Figma API credentials configured
- [ ] Test screen configurations in place
- [ ] Test files and directories cleaned

### Test Execution
- [ ] REST API tests completed
- [ ] MCP tools tests completed
- [ ] Figma integration tests completed
- [ ] Batch search tests completed
- [ ] Edge cases tested
- [ ] Performance tests completed
- [ ] Security tests completed

### Post-Test Cleanup
- [ ] Test data cleaned from database
- [ ] Temporary files deleted
- [ ] Test logs archived
- [ ] Test results documented

---

## Test Reporting Template

| Test ID | Test Case | Status | Notes | Issues |
|---------|-----------|--------|-------|--------|
| TC-LANG-001 | Get all languages | ✅ PASS | - | - |
| TC-TRANS-001 | Get all translations | ✅ PASS | - | - |
| TC-FIGMA-BATCH-001 | Batch search all found | ⏳ PENDING | - | - |
| ... | ... | ... | ... | ... |

---

## Automation Recommendations

1. **REST API Tests**: Use pytest with requests library
2. **MCP Tool Tests**: Use pytest with async MCP client
3. **Figma Tests**: Mock Figma API responses for unit tests
4. **Database Tests**: Use pytest fixtures with test database
5. **Performance Tests**: Use locust for load testing
6. **CI/CD Integration**: Run tests on every commit

---

## Notes

- All Figma API calls should be mocked in unit tests
- Use test database separate from production
- Batch performance should be significantly better than individual calls
- Monitor Figma API rate limits during testing
- Log all test failures with detailed error messages
