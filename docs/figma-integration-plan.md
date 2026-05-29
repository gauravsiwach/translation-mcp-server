# Figma Integration Implementation Plan

This plan documents the complete Figma integration implementation for the translation MCP server, enabling automatic frame detection and visual confirmation in the MCP workflow.

## Overview

The Figma integration connects translation keys to their visual design counterparts in Figma, allowing:
1. **Automatic frame detection** - Find Figma frames by matching frame names with translation text
2. **Visual confirmation** - Show screenshot previews to users before saving
3. **Metadata storage** - Store `figma_file_key`, `figma_node_id`, and `figma_screenshot_url` with translations

## Current Implementation Status

### ✅ Completed Components

#### 1. Database Schema (`src/db/models.py`)
- **Translation model** already has Figma fields:
  - `figma_node_id` (String 128) - Figma node identifier
  - `figma_file_key` (String 255) - Figma file identifier  
  - `figma_screenshot_url` (Text) - CDN URL for frame screenshot
  - `screen_id` (String 128) - **NOT USED** for Figma integration (exists for other purposes)

#### 2. Figma Client (`src/ai/figma_client.py`)
**Key functions:**
- `fetch_image_urls(file_key, node_ids, format="png")` - Fetches screenshot URLs from Figma Images API
- `fetch_file_document(file_key, node_ids=None)` - Fetches Figma file structure with optional node filtering
  - **Critical fix**: Added `node_ids` parameter with `?ids=` query param to avoid "Request too large" errors
  - Timeout set to 600 seconds for large files

**Implementation details:**
```python
# URL construction with node filtering
if node_ids:
    ids_param = ",".join(node_ids)
    url = f"https://api.figma.com/v1/files/{quote(file_key)}?ids={quote(ids_param)}"
```

#### 3. Figma Service (`src/services/figma_service.py`)
**Core functions:**

**a. `_extract_all_frames(node, frames=None, depth=0)`**
- Recursively extracts all FRAME nodes from document
- For each frame, extracts all text content within it
- Returns: `[{id, name, type, texts: [...], depth}, ...]`

**b. `_extract_text_from_frame(node)`**
- Recursively extracts text from TEXT nodes with `characters` field
- Returns list of text strings found in frame

**c. `find_node_by_text(screen_id, default_text)`**
- Main search function exposed to MCP
- **Note:** `screen_id` parameter is used to look up config from `figma_screens.json`, NOT the database field
- Flow:
  1. Get screen config from `figma_screens.json` using `screen_id` parameter
  2. Call `fetch_file_document(file_key, node_ids)` with filtered nodes
  3. Extract all FRAME nodes with `_extract_all_frames()`
  4. **Exact match** frame name with search text (case-insensitive, stripped)
  5. Skip instance IDs (containing semicolons like `"I35773:133678;30142:75897"`)
  6. Return first matching non-instance frame
- Returns: `{figma_file_key, figma_node_id}` or `{figma_file_key, figma_node_id: None}`

**Key implementation:**
```python
# Exact match logic
search_text = default_text.lower().strip()
for frame in all_frames:
    frame_name = frame.get("name", "").lower().strip()
    if search_text == frame_name:
        if ";" not in frame_id:  # Skip instances
            return {"figma_file_key": figma_file_key, "figma_node_id": frame_id}
```

**d. `update_figma_metadata(session, key, market_code, figma_file_key, figma_node_id, figma_screenshot_url)`**
- Updates Figma metadata for all translations matching key + market
- Stores file_key, node_id, and screenshot_url

**e. `get_figma_info(session, key, market_code)`**
- Retrieves stored Figma metadata for a translation
- Returns: `{figma_file_key, figma_node_id, figma_screenshot_url, figma_url}`

#### 4. Screen Configuration (`src/figma_screens.json`)
Maps screen IDs to Figma file keys and node IDs:
```json
{
  "home": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_page_name": "Home Screen",
    "nodes": ["35773:267354"]
  }
}
```

#### 5. MCP Tools (`src/mcp/tools/translation_tools.py`)
**a. `get_figma_screenshot_url(figma_file_key, figma_node_id)`**
- Calls `fetch_image_urls()` from figma_client
- Returns: `{figma_file_key, figma_node_id, screenshot_url}`
- Pure API call, no DB interaction

**b. `find_figma_node_by_text(screen_id, default_text)`**
- Calls `find_node_by_text()` from figma_service
- Returns: `{figma_file_key, figma_node_id}` or `{figma_node_id: None}`

**c. `get_figma_screen_config(screen_id=None)`**
- Returns screen config from `figma_screens.json`
- If screen_id omitted, returns full mapping

**d. `update_translation_figma(key, figma_file_key, figma_node_id)`**
- Fetches screenshot URL
- Updates all market rows for the key with Figma metadata

**e. `get_figma_info_tool(key, market_code=None)`**
- Retrieves stored Figma metadata for a key

#### 6. Translation Service Integration (`src/services/translation_service.py`)
**`save_direct_translations()` function:**
- Accepts optional Figma fields in translation dict:
  - `figma_file_key`
  - `figma_node_id`
  - `figma_screenshot_url`
- Stores Figma metadata directly when creating/updating translations
- Atomic transaction - all translations + Figma data saved together

#### 7. MCP Workflow Rules (`mcp_client/.windsurfrules`)
**Step B - Figma Node Selection (Smart Matching):**

**Case B.2 - Match found:**
1. Call `find_figma_node_by_text(screen_id, default_text)`
2. If match found:
   - Call `get_figma_screenshot_url(figma_file_key, figma_node_id)`
   - **Show image in chat**: `![Figma Screenshot]({figma_screenshot_url})`
   - Display node ID
   - Ask: "Is this the correct Figma frame? (yes/no)"
   - **WAIT for confirmation**
   - If yes → store metadata and proceed
   - If no → ask for manual input or skip

**Case B.3 - No match:**
1. Ask user to paste Figma link manually or skip
2. If link provided:
   - Extract node ID
   - Call `get_figma_screenshot_url()`
   - Show image preview
   - Ask for confirmation

**Case C - No screen config:**
1. Ask user for manual Figma link or skip
2. Show preview and confirm

**Step D - Save Everything:**
1. For keys with `figma_node_id` set:
   - Call `get_figma_screenshot_url()` to get URL
2. Assemble full payload with all Figma fields
3. Call `save_translations()` once with complete data
4. Single atomic DB transaction

#### 8. Debug Endpoint (`src/api/translations.py`)
**Temporary endpoint for testing:**
```python
@router.get("/debug/find-node-by-text", status_code=200)
async def debug_find_node_by_text(screen_id: str, default_text: str):
    result = await find_node_by_text(screen_id, default_text)
    return result
```
**Status:** Can be removed after testing is complete

## Implementation Challenges Solved

### 1. "Request too large" Error
**Problem:** Figma API returned 400 error when fetching entire file
**Solution:** Added `node_ids` parameter to `fetch_file_document()` to filter response using `?ids=` query param

### 2. Frame vs Instance IDs
**Problem:** Figma returns both actual frames and instance IDs (with semicolons)
**Solution:** Filter out IDs containing semicolons: `if ";" not in frame_id`

### 3. Text Search Approach
**Evolution:**
- ❌ Initial: Search TEXT node characters recursively → too complex
- ❌ Second: Match FRAME names by partial match → matched wrong frames
- ✅ Final: **Exact match** on FRAME names (case-insensitive, stripped)

### 4. User Confirmation Flow
**Problem:** Auto-saving without visual confirmation could link wrong frames
**Solution:** 
- Show actual screenshot image in chat using markdown
- Wait for explicit user confirmation
- Allow manual override or skip

## File Structure

```
src/
├── ai/
│   └── figma_client.py          # Figma API client (fetch_image_urls, fetch_file_document)
├── services/
│   ├── figma_service.py         # Frame search logic (find_node_by_text, update/get metadata)
│   └── translation_service.py   # save_direct_translations with Figma fields
├── mcp/
│   └── tools/
│       └── translation_tools.py # MCP tools (get_figma_screenshot_url, find_figma_node_by_text)
├── api/
│   └── translations.py          # Debug endpoint (temporary)
├── db/
│   └── models.py                # Translation model with Figma fields
└── figma_screens.json           # Screen → Figma file/node mapping

mcp_client/
└── .windsurfrules               # MCP workflow with visual confirmation
```

## Environment Variables Required

```bash
FIGMA_ACCESS_TOKEN=figd_...     # Figma personal access token
```

## Testing

### Manual Testing via Debug Endpoint
```bash
GET /api/v1/debug/find-node-by-text?screen_id=home&default_text=Easy%20order
```

### Expected Response
```json
{
  "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
  "figma_node_id": "35773:133679"
}
```

### MCP Testing Flow
1. Start MCP server: `python src/mcp/server.py`
2. In IDE/AI assistant: "Add translation key home.easy_order with text 'Easy order' for market IN"
3. MCP should:
   - Find Figma node automatically
   - Show screenshot image
   - Ask for confirmation
   - Save with Figma metadata after approval

## Migration to New Branch

### Files to Include
1. **Core Implementation:**
   - `src/ai/figma_client.py` (with node_ids filtering)
   - `src/services/figma_service.py` (complete implementation)
   - `src/mcp/tools/translation_tools.py` (Figma tools)
   - `src/services/translation_service.py` (Figma field handling)
   - `src/figma_screens.json` (screen config)
   - `mcp_client/.windsurfrules` (updated workflow)

2. **Database:**
   - `src/db/models.py` (already has Figma fields)
   - No new migrations needed

3. **API:**
   - `src/api/translations.py` (debug endpoint - optional)

### Files to Exclude
- `test_figma_text_search.py` (not needed in production)
- `src/api/figma_frames_*.json` (debug output files)
- `src/api/figma_response.json` (debug file)

## Key Decisions & Rationale

### 1. Exact Match vs Partial Match
**Decision:** Use exact frame name matching
**Rationale:** 
- Partial matching returned wrong frames (e.g., "Easy order" matched "Easy order header")
- Exact match is more predictable and reliable
- Fallback to manual input handles edge cases

### 2. Show Image in Chat
**Decision:** Display actual screenshot using markdown `![](url)`
**Rationale:**
- Visual confirmation prevents linking wrong frames
- User can immediately see if match is correct
- Reduces errors and rework

### 3. Node ID Filtering in API Call
**Decision:** Pass `node_ids` to Figma API
**Rationale:**
- Prevents "Request too large" errors for big files
- Faster response times
- Only fetches relevant nodes from config

### 4. Skip Instance IDs
**Decision:** Filter out IDs with semicolons
**Rationale:**
- Instance IDs like `"I35773:133678;30142:75897"` are component instances
- Actual frame IDs are simpler: `"35773:133679"`
- Instances can't be used for screenshots

## Next Steps (Post-Migration)

1. **Remove debug endpoint** after testing confirms everything works
2. **Add more screens** to `figma_screens.json` as needed
3. **Monitor logs** for any "no match" cases to improve matching logic
4. **Consider fuzzy matching** as future enhancement if exact match is too strict
5. **Add Figma integration docs** to README (optional)

## Success Criteria

- ✅ `find_node_by_text()` returns correct frame ID for exact name matches
- ✅ Screenshot URLs are fetched and displayed in MCP chat
- ✅ User confirmation flow works before saving
- ✅ Figma metadata is stored atomically with translations
- ✅ No "Request too large" errors from Figma API
- ✅ Instance IDs are properly filtered out

## Important Clarifications

### screen_id Usage
- **Translation model `screen_id` field:** NOT used for Figma integration (exists for other purposes)
- **`find_node_by_text(screen_id, ...)` parameter:** Used to look up configuration from `figma_screens.json`
- These are separate concepts - the function parameter is for config lookup, the DB field is unrelated to Figma

### Configuration Flow
1. User provides `screen_id` (e.g., "home", "basket") when calling MCP tool
2. System looks up `screen_id` in `figma_screens.json` to get `figma_file_key` and `nodes`
3. System searches Figma using that configuration
4. Results (`figma_file_key`, `figma_node_id`, `figma_screenshot_url`) are stored in Translation model
5. The `screen_id` DB field is NOT populated or used in this process

## Notes

- **Figma API rate limits:** Be aware of rate limits when testing
- **Screenshot URL expiry:** Figma CDN URLs may expire; consider refresh logic if needed
- **Screen config maintenance:** `figma_screens.json` needs manual updates for new screens
- **Error handling:** All Figma operations have try/catch with proper logging
