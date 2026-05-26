# Smart Figma Node Matching by Text Content

This plan adds intelligent Figma node matching that automatically finds the layer containing the translation text using the Figma REST API, eliminating manual URL selection during translation creation.

## Current Flow (Manual - Step B in Two-Step Translation Flow)
1. Get screen config (file_key, node_ids)
2. Build Figma URLs for each node
3. Show list to user
4. User manually selects which node contains their text
5. Store node_id for Step D

## New Flow (Smart/Automated - Step B in Two-Step Translation Flow)
1. Get screen from user (already extracted from key prefix)
2. Get screen config (file_key, node_ids)
3. Call Figma REST API to get node details including text content for all nodes
4. Search for `default_text` in node text content (case-insensitive)
5. **If match found** → auto-use first matching node
6. **If no match** → ask user to paste Figma node link manually or skip
7. Continue to Step C (translation review)

## Implementation Steps

### Step 1: Add Figma REST API client for node details
**File:** `src/ai/figma_client.py`

Add new function `fetch_node_details(file_key, node_ids)`:
- Calls `https://api.figma.com/v1/files/{file_key}?ids={node_id}`
- Returns node details including text content for each node
- Uses existing `FIGMA_ACCESS_TOKEN` from settings
- Follows same error handling pattern as `fetch_image_urls`

### Step 2: Add smart node matching service function
**File:** `src/services/figma_service.py`

Add new function `find_node_by_text(screen_id, default_text)`:
- Gets screen config (file_key, node_ids) from `figma_screens.json`
- Calls `fetch_node_details` for all node_ids in the screen
- Searches for `default_text` in node text content (case-insensitive)
- **Returns first matching node_id** or None
- Simple return: `{"figma_file_key": "...", "figma_node_id": "..." or None}`

### Step 3: Add new MCP tool for smart node matching
**File:** `src/mcp/tools/translation_tools.py`

Add new tool `find_figma_node_by_text(screen_id, default_text)`:
- Calls `find_node_by_text` service function
- Returns matching node_id or None
- Simple response: `{"matched": true/false, "node_id": "...", "figma_file_key": "..."}`

### Step 4: Update windsurf rules - Step B only
**File:** `mcp_client/.windsurfrules`

**Replace "Step B — Figma node selection" section (lines 205-241)** with simplified smart matching:

```
### Step B — Figma node selection (Smart Matching)

Run this BEFORE showing translations to the user.
**Do NOT call any Figma MCP tool here.** All data comes from `get_figma_screen_config` called in Step A.

**Case A — User already provided `figma_node_id` explicitly:**
Skip. Store `{figma_file_key, figma_node_id}`. Go to Step C.

**Case B — Screen config available from Step A:**
1. Call `find_figma_node_by_text(screen_id, default_text)` silently
2. If match found → store `{figma_file_key, figma_node_id}` → go to Step C
3. If no match → ask user:
   "No matching Figma node found for '{default_text}' on screen '{screen_id}'.
    Would you like to:
    1. Paste a Figma node link manually
    2. Skip Figma linking for this key"
   
   WAIT for response:
   - 1 → extract node-id from URL → store it
   - 2 → store figma = null

**Case C — No screen config found:**
Same as current (ask for manual link or skip)
```

**Keep all other sections unchanged** - only Step B changes to use smart matching.

## Technical Details

### Figma REST API Endpoint
```
GET https://api.figma.com/v1/files/{file_key}?ids={node_id}
Headers: X-Figma-Token: {token}
```

Response includes node structure with text content that can be searched.

### Case-Insensitive Matching
Use `default_text.lower()` to match against node text content, ignoring case for broader coverage.

### Multiple Match Handling
**Auto-select first match** - if multiple nodes contain the same text, automatically use the first one found.

### Fallback
If no match found:
- Ask user to paste Figma node link manually
- Or skip Figma linking for this key

## Integration Summary

**What changes:**
- Only Step B in the Two-Step Translation Flow (windsurf rules lines 205-241)
- Backend adds 1 new MCP tool: `find_figma_node_by_text`
- Backend adds 2 new functions: `fetch_node_details` (client), `find_node_by_text` (service)

**What stays the same:**
- All other windsurf rule sections unchanged
- Step A, C, D remain identical
- Figma Sync Workflow (standalone) unchanged
- All existing MCP tools unchanged

**User experience:**
- During translation creation, Figma node matching happens automatically
- User only interacts if no match found (paste link or skip)
- Simpler, faster workflow - no manual URL browsing

## Testing
1. Test with known matching text (should find node automatically)
2. Test with non-matching text (should ask for manual link)
3. Test with multiple matches (should auto-use first)
4. Test case-insensitive matching
