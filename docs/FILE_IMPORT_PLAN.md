# File-Based Translation Import Feature

Add REST API endpoints for file upload/download and Windsurf rules to guide AI in processing attached translation files using existing MCP tools, enabling both direct API access and AI-assisted file processing workflows.

## Overview

Users can upload translation files (CSV/JSON) containing keys and translations for multiple locales. The system will:
1. Validate file structure and locale columns
2. Upsert existing translations from the file
3. Use AI to generate missing translations (using 'en' as source)
4. Process large files asynchronously using existing batch system
5. Allow users to download the completed file with all translations

## File Format

**CSV Example:**
```csv
type,key,en,hi_IND
Simple text,account.club_title_label,About Club,क्लब के बारे में
Simple text,account.how_can_we_help,Hi [name], how can we help?,नमस्ते [name], हम कैसे मदद कर सकते हैं?
```

**JSON Example:**
```json
[
  {
    "type": "Simple text",
    "key": "account.club_title_label",
    "en": "About Club",
    "hi_IND": "क्लब के बारे में"
  }
]
```

**Rules:**
- Required columns: `type`, `key`, `en`
- Additional columns must be valid Pepsi locale codes from `pepsi_languages` table
- `en` is always the source language for AI translation
- Source language (en) translations are upserted to the database to ensure entries exist
- If a locale column has a value, skip AI translation for that key+locale (configurable via env)

## Implementation Plan

### 1. Configuration (Environment Variables)

**File:** `src/config.py` (create if doesn't exist)
```python
SKIP_AI_IF_VALUE_EXISTS = True  # Skip AI translation if locale value exists in file
SOURCE_LANGUAGE = "en"  # Source language for AI translation
MAX_FILE_SIZE_MB = 10  # Maximum file size
```

### 2. File Processing Service

**File:** `src/services/file_service.py` (new)

**Functions:**
- `parse_csv_file(file_content: bytes) -> List[Dict]`
  - Parse CSV file into list of dicts
  - Validate structure (type, key, en columns exist)
  
- `parse_json_file(file_content: bytes) -> List[Dict]`
  - Parse JSON file
  - Validate structure
  
- `validate_locale_columns(columns: List[str], valid_locales: List[str]) -> Dict`
  - Check all non-required columns are valid Pepsi locales
  - Return validation result with errors
  
- `prepare_translation_items(rows: List[Dict], locale_columns: List[str]) -> Dict`
  - Split into two groups:
    - Existing translations (upsert directly) - includes source language (en) and filled locale columns
    - Missing translations (need AI) - empty locale columns only
  - Return both groups

- `generate_output_file(batch_id: str, format: str) -> bytes`
  - Fetch all translations for keys in batch from database
  - Generate CSV/JSON with all locales filled
  - Return file bytes

### 3. Batch Status Enhancement

**File:** `src/services/translation_service.py`

**Update existing `batch_status` dict to store:**
```python
batch_status[batch_id] = {
    "status": "processing",  # processing, completed, failed
    "total": total_items,
    "completed": 0,
    "pending": total_items,
    "failed": 0,
    "file_type": "csv",  # csv or json
    "keys": [...],  # List of keys being processed
    "results": [],
    "error": None
}
```

### 4. REST API Endpoints

**File:** `src/api/translations.py`

#### POST /translations/upload
- **Purpose:** Upload and process translation file
- **Request:** 
  - `multipart/form-data` with file
  - Query param: `format` (csv or json)
- **Validation:**
  - File size < MAX_FILE_SIZE_MB
  - Valid CSV/JSON structure
  - Required columns exist (type, key, en)
  - All locale columns are valid Pepsi locales
- **Processing:**
  1. Parse file
  2. Validate locale columns against `pepsi_languages`
  3. Prepare translation items (existing vs missing)
  4. Upsert existing translations via `create_translation` (includes source language 'en' and filled locale columns)
  5. Generate missing translations via `ai_translate` (async if >10 items)
  6. Return batch_id for tracking
- **Response:**
  ```json
  {
    "batch_id": "uuid",
    "status": "processing",
    "total_keys": 100,
    "message": "File is being processed. Check status using batch_id."
  }
  ```

#### GET /translations/batch/{batch_id}/download
- **Purpose:** Download completed translation file
- **Query params:** 
  - `format` (csv or json)
- **Validation:**
  - Batch exists
  - Batch status is "completed"
- **Response:**
  - File download with all translations filled
  - Filename: `translations_{batch_id}.{format}`

### 5. Schema Updates

**File:** `src/api/schemas/translations.py`

**New schemas:**
```python
class FileUploadResponse(BaseModel):
    batch_id: str
    status: str
    total_keys: int
    message: str

class FileValidationError(BaseModel):
    error: str
    details: Optional[Dict] = None
```

### 6. Processing Flow

```
1. User uploads file → POST /translations/upload
2. System validates file structure and locales
3. System splits into:
   - Existing translations → upsert via create_translation
   - Missing translations → AI translate via ai_translate
4. System returns batch_id
5. User polls → GET /translations/batch/{batch_id}/status
6. When complete → GET /translations/batch/{batch_id}/download
```

### 7. Error Handling

- **Invalid file format:** 400 with validation errors
- **Invalid locale columns:** 400 with list of invalid locales
- **File too large:** 413 Payload Too Large
- **Batch not found:** 404
- **Batch not completed:** 400 with current status
- **Processing errors:** Store in batch_status["error"]

## Files to Create/Modify

### New Files
1. `src/config.py` - Configuration settings
2. `src/services/file_service.py` - File parsing and validation
3. `src/api/schemas/file.py` - File upload schemas (optional, can add to translations.py)

### Modified Files
1. `src/services/translation_service.py` - Enhance batch_status structure
2. `src/api/translations.py` - Add upload and download endpoints
3. `src/api/schemas/translations.py` - Add FileUploadResponse schema

## Testing Checklist

- [ ] Upload valid CSV file with all locales filled
- [ ] Upload CSV file with missing translations (triggers AI)
- [ ] Upload JSON file
- [ ] Upload file with invalid locale columns (should fail validation)
- [ ] Upload file >10 items (should use async batch processing)
- [ ] Download completed file in CSV format
- [ ] Download completed file in JSON format
- [ ] Poll batch status while processing
- [ ] Handle file with duplicate keys

## MCP Integration (Windsurf Rules)

### 8. Windsurf Rules for File Processing

**File:** `mcp_client/.windsurfrules`

**Concept:** Instead of creating file upload MCP tools, leverage Windsurf's ability to read attached files and guide the AI to use existing MCP tools (`ai_translate`, `create_translation`) in batches.

**No new MCP tools needed** - Windsurf reads files and orchestrates existing tools.

### 9. Windsurf Rules Content

Add new section to `.windsurfrules`:

```markdown
## File-Based Translation Import

### When to use
- User attaches a CSV/JSON translation file
- User wants to bulk import/update translations
- User says "process this translation file" or similar

### File Format Requirements
- **Required columns:** `type`, `key`, `en`
- **Optional columns:** Any valid Pepsi locale codes (e.g., `hi_IND`, `es_ES`)
- **Source language:** Always `en` (English)
- **Empty cells:** Trigger AI translation
- **Filled cells:** Skip AI translation (upsert directly)

### API Mode Workflow

When user attaches a translation file:

1. **Read and validate file:**
   ```
   - Read file content (Windsurf can read attached files)
   - Parse CSV/JSON structure
   - Validate required columns exist (type, key, en)
   - Validate locale columns against list_languages()
   - If validation fails, explain errors to user
   ```

2. **Process existing translations:**
   ```
   - For each row:
     - Add source language (en) translation to upsert list
     - For each filled locale value, add to upsert list
     - Call create_translation() with all upsert items
   - Process in batches of 10 using create_translation array input
   ```

3. **Process missing translations (AI):**
   ```
   - For each row with empty locale values:
     - Get target locales from file columns
     - Call ai_translate() with:
       {
         "label": row.key,
         "source_text": row.en,
         "target_language_codes": [empty_locales],
         "type": row.type
       }
   - Process in batches of 10 (auto sync/async)
   - If >10 items, inform user about batch_id for tracking
   ```

4. **Report results:**
   ```
   - Show summary: X keys processed, Y translations created, Z AI-generated
   - If async batch, provide batch_id and suggest checking status
   - Offer to download updated file via REST API
   ```

### Tool Mode Workflow

When user attaches a translation file in Tool mode:

1. **Read and validate file** (same as API mode)

2. **Ask user for confirmation:**
   ```
   "I found X keys in the file. Y have existing translations, Z need AI translation.
   Shall I proceed with:
   - Upserting Y existing translations
   - AI translating Z missing translations for locales: [list]"
   ```

3. **Process with create_translation tool:**
   ```
   - Use create_translation() for all rows (upsert logic handles existing)
   - Process in batches of 10
   ```

4. **Process missing with ai_translate tool:**
   ```
   - For rows with empty locales, call ai_translate()
   - Process in batches of 10
   - Track batch_id if async
   ```

5. **Report results** (same as API mode)

### Example Interaction

**User:** "Process this translation file" [attaches translations.csv]

**AI Response:**
```
I've read your translation file with 25 keys:
- 15 keys have hi_IND translations (will upsert)
- 10 keys need AI translation for hi_IND
- All keys have 'en' source text

Validating locale columns... ✓ All valid

Processing:
1. Upserting 15 existing translations...
   ✓ Batch 1 (10 items) completed
   ✓ Batch 2 (5 items) completed

2. AI translating 10 missing translations...
   ✓ Batch created (batch_id: abc-123)
   Status: Processing

Check status: get_batch_status("abc-123")
Download updated file: GET /translations/batch/abc-123/download?format=csv
```

### Error Handling

- **Invalid file format:** Explain expected CSV/JSON structure
- **Missing required columns:** List missing columns (type, key, en)
- **Invalid locale columns:** List invalid locales, suggest valid ones from list_languages()
- **Empty file:** Inform user and ask for valid file
- **Duplicate keys:** Warn user, last occurrence wins (upsert behavior)
```

## Future Enhancements (Not in this phase)

- Support for Excel files (.xlsx)
- Bulk delete via file
- File upload history/audit log
- Progress percentage in batch status
- Email notification when processing complete
- Streaming file upload for very large files
