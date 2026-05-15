# Figma Integration Plan

> **Last updated: 14 May 2026**

---

## Overview

Link translation keys to Figma screen designs so BAs can visually review translations against the actual UI designs.

**Design principles:**
- BA/dev manually maintains `src/figma_screens.json` — committed to git, no secrets
- No Figma MCP tools used — node selection is entirely user-driven via URL list
- Figma REST API (`/v1/images`) fetches a CDN PNG screenshot per node
- Everything (translation + figma info) saved in one DB write
- Token stays in `.env`, never committed

---

## Architecture

### DB columns (on `translations` table)

| Column | Type | Notes |
|---|---|---|
| `figma_node_id` | `String(128)` | e.g. `35773:267354` |
| `figma_file_key` | `String(255)` | e.g. `Fr5237RlW3syTjaBAB1kMN` |
| `figma_screenshot_url` | `Text` | CDN PNG URL from Figma Images API |

All nullable. Same values written to all market rows for a key.

### `src/figma_screens.json`

BA edits this file and commits. Structure:

```json
{
  "home": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_page_name": "Home Screen",
    "nodes": ["35773:267354", "35773:267356", "35505:113695"]
  },
  "basket": {
    "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
    "figma_page_name": "Product Catalog",
    "nodes": ["31157:391595", "16597:291324", "18747:109494"]
  }
}
```

`nodes` = top-level section frame IDs. Get them from Figma: right-click frame → Copy link → extract `node-id` from URL.

### Key files

| File | Purpose |
|---|---|
| `src/figma_screens.json` | Screen config. Committed to git. |
| `src/config.py` | `FIGMA_ACCESS_TOKEN: Optional[str]` |
| `src/ai/figma_client.py` | `fetch_image_urls(file_key, node_ids)` — Figma REST `/v1/images` |
| `src/utils/figma_config.py` | `load_figma_screens()`, `get_screen_config(screen_id)`, `list_screens()` |
| `src/services/figma_service.py` | `update_translation_figma_info()`, `get_figma_info()` |
| `src/services/translation_service.py` | `save_direct_translations()` — extended to accept figma fields |
| `src/mcp/tools/translation_tools.py` | All MCP tools in single `register()` |
| `mcp_client/.windsurfrules` | Windsurf AI assistant rules + user flow |

---

## MCP Tools

| Tool | Purpose | DB? |
|---|---|---|
| `get_figma_screen_config(screen_id?)` | Read `figma_screens.json` | No |
| `get_figma_screenshot_url(figma_file_key, figma_node_id)` | Fetch CDN PNG URL from Figma REST API | No |
| `save_translations([...])` | Save translation rows — accepts optional figma fields | Yes — one write |
| `update_translation_figma(key, figma_file_key, figma_node_id)` | Standalone sync: fetch screenshot + update existing rows | Yes |
| `get_figma_info_tool(key, market_code?)` | Return stored Figma metadata + deep link for a key | Read only |

> `register_figma_screen` is **disabled** — BA edits `figma_screens.json` directly.

---

## User Flow (Tool Mode — Add Key with Figma)

### Step A — Silent background (no user interaction)

AI infers `key`, `default_text`, `market_code`, `screen_id` from the message, shows summary, waits for confirmation. After confirmation:

```
1. get_figma_screen_config(screen_id)
   → store figma_file_key + all node IDs for that screen

2. get_translations(market_code, environment="DEV")
   → check if key already exists
   EXISTS → stop, show existing value, ask: update or new key name
   NEW    → continue

3. prepare_translations(items)
   → resolve default_locale + target locales
```

No confirmation prompt for these read-only calls.

### Step B — Figma node selection (user picks)

AI builds one URL per configured node and shows them:

```
"Here are the Figma sections for the `home` screen (Figma page: Home Screen).
 Which one contains `Expires in 8 hours`?

 1. https://www.figma.com/design/Fr5237RlW3syTjaBAB1kMN?node-id=35773:267354
 2. https://www.figma.com/design/Fr5237RlW3syTjaBAB1kMN?node-id=35773:267356
 3. https://www.figma.com/design/Fr5237RlW3syTjaBAB1kMN?node-id=35505:113695
 4. None of these (paste a different node link)
 5. Skip Figma linking for this key"
```

- 1/2/3 → store `figma_node_id` + `figma_file_key`
- 4 → ask for link → extract `node-id` from URL → store it
- 5 / skip → `figma = null` (translation saves without Figma)
- No screen config → ask user to paste a node link or skip

No Figma MCP tools called here.

### Step C — Translation review (user approves)

AI translates `default_text` into each locale, shows table with confidence score. Waits for approval. User can request changes before saving.

```
| # | Key                     | Locale | Translation             | Confidence |
|---|-------------------------|--------|-------------------------|------------|
| 1 | home.expires_in_8_hours | hi_IND | 8 घंटे में समाप्त होगा | 0.95       |
```

### Step D — Save in one shot (no more user interaction)

```
1. get_figma_screenshot_url(figma_file_key, figma_node_id)
   → Figma REST API → returns CDN PNG URL
   → no DB write

2. save_translations([{
     key, market_code, default_text,
     locale_code, value, confidence=1.0,
     figma_file_key, figma_node_id, figma_screenshot_url   ← from step 1
   }])
   → ONE DB write — translation + figma info saved atomically
```

If user skipped Figma (step B = null): only `save_translations` with no figma fields.

Shows result:

| Key | Locale | Value | Figma node | Screenshot |
|---|---|---|---|---|
| home.expires_in_8_hours | hi_IND | 8 घंटे में समाप्त होगा | 35773:267354 | ✅ saved |

Then asks: "What would you like to do next?"

---

## Standalone Figma Sync (existing keys)

When user says "sync figma for `home.flash_deal`":

```
1. get_figma_screen_config(screen_id)  →  node list + file_key

2. Show URL list to user → user picks node

3. update_translation_figma(key, figma_file_key, figma_node_id)
   → fetches PNG from Figma REST API
   → updates figma_file_key, figma_node_id, figma_screenshot_url
     on ALL existing market rows for that key
```

---

## Code Changes Required (Phase 2)

| File | Change |
|---|---|
| `src/ai/figma_client.py` | Fix URL encoding bug: `ids={quote(ids_param)}` → `ids={ids_param}` — `quote()` encodes `:` as `%3A`, breaking node IDs like `35773:267354` |
| `src/mcp/tools/translation_tools.py` | Add `get_figma_screenshot_url(figma_file_key, figma_node_id)` — calls `fetch_image_urls`, returns `{screenshot_url}`, no DB access |
| `src/services/translation_service.py` | `save_direct_translations()`: read optional `figma_file_key`, `figma_node_id`, `figma_screenshot_url` from each item dict, write to `Translation` row in the same transaction |
| `mcp_client/.windsurfrules` | Update Step D to use `get_figma_screenshot_url` first then `save_translations` with figma fields; add `get_figma_screenshot_url` to allowed tools list |

---

## Verification

1. `get_figma_screenshot_url("Fr5237RlW3syTjaBAB1kMN", "35773:267354")` → returns CDN PNG URL (confirms encoding bug fixed)
2. Add a key end-to-end → result table shows screenshot URL, no second tool call
3. DB row has `figma_screenshot_url`, `figma_file_key`, `figma_node_id` all set from a single `save_translations` call
4. Standalone sync: `update_translation_figma` updates existing rows correctly

---

## Out of Scope

- REST API endpoints (planned after MCP flows stable)
- Figma webhook / auto-sync on file change
- S3 / blob storage (Figma CDN URLs used directly)
- Figma plugin
- Auto text-matching (removed — unreliable, replaced by user-driven URL selection)


### Step 1 — Model Update
- File: `src/db/models.py`
- Add 2 new columns to the `Translation` class:
  - `figma_file_key = Column(String(255), nullable=True)`
  - `figma_screenshot_url = Column(Text, nullable=True)`
- Note: `figma_node_id` already exists on the table — no change needed
- POC mode: app will auto-sync schema on startup

### Step 2 — Figma Screens Config
- File: `src/figma_screens.json` (new file, committed to git)
- Structure:
```json
{
  "basket": {
	 "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
	 "figma_page_name": "Basket / Cart",
	 "nodes": ["16033:237370"]
  },
  "home": {
	 "figma_file_key": "Fr5237RlW3syTjaBAB1kMN",
	 "figma_page_name": "Home Screen",
	 "nodes": ["12345:100"]
  }
}
```
- `nodes` = top-level section frame IDs only (not leaf text nodes)
- BA gets node ID from Figma: right-click frame → Copy link → extract `node-id` from URL

### Step 3 — Config Setting
- File: `src/config.py`
- Add: `FIGMA_ACCESS_TOKEN: Optional[str] = None`
- Add `FIGMA_ACCESS_TOKEN=your_token` to `.env` (not committed)

---

## Phase 2 — Backend Services

### Step 4 — Figma REST API Client
- File: `src/ai/figma_client.py` (new)
- Uses `httpx` (already in `requirements.txt`) — no new dependency
- Single async function:
  ```python
  async def fetch_image_urls(file_key: str, node_ids: list[str]) -> dict[str, str]
  ```
  - Calls: `GET https://api.figma.com/v1/images/{file_key}?ids={node_ids}&format=png`
  - Auth header: `X-Figma-Token: {settings.FIGMA_ACCESS_TOKEN}`
  - Returns: `{ "node_id": "https://cdn.figma.com/..." }`

### Step 5 — Figma Service
- File: `src/services/figma_service.py` (new)
- Functions:
  1. `update_translation_figma_info(session, key, figma_file_key, figma_node_id) -> dict`
	  - Calls `figma_client.fetch_image_urls` to get screenshot CDN URL
	  - Updates `figma_file_key`, `figma_node_id`, `figma_screenshot_url` on ALL market rows for that key
	  - Returns result summary: rows updated, screenshot URL
  2. `get_figma_info(session, key, market_code) -> dict`
	  - Returns `figma_file_key`, `figma_node_id`, `figma_screenshot_url` for a key + market
	  - Also computes and returns `figma_url` deep link: `https://www.figma.com/design/{file_key}?node-id={node_id}`

---

## Phase 3 — New MCP Tools

### Step 6 — 4 New MCP Tools
- File: `src/mcp/tools/translation_tools.py` — add to existing `register()` function

#### Tool 1: `register_figma_screen`
- **Purpose:** BA registers a new screen config into `src/figma_screens.json`
- **Params:** `screen_id`, `figma_file_key`, `figma_page_name`, `node_ids: list[str]`
- **Action:** Reads `src/figma_screens.json`, adds/updates the entry, writes back
- **Returns:** `{ "screen_id": "basket", "status": "saved", "config": {...} }`

#### Tool 2: `get_figma_screen_config`
- **Purpose:** Read screen config — used by Windsurf before calling Figma MCP
- **Params:** `screen_id` (optional — if omitted returns all screens)
- **Action:** Reads `src/figma_screens.json`, returns matching entry or all entries
- **Returns:** config dict for the screen(s)

#### Tool 3: `update_translation_figma`
- **Purpose:** Save Figma node + fetch screenshot URL and persist to DB
- **Params:** `key`, `figma_file_key`, `figma_node_id`
- **Action:** Calls `figma_service.update_translation_figma_info` → fetches CDN URL → saves to all market rows
- **Returns:** `{ "key": "basket.title", "figma_node_id": "...", "figma_screenshot_url": "...", "rows_updated": 2 }`

#### Tool 4: `get_figma_info`
- **Purpose:** Return all Figma metadata for a translation key
- **Params:** `key`, `market_code`
- **Action:** Calls `figma_service.get_figma_info`
- **Returns:** `{ "figma_file_key": "...", "figma_node_id": "...", "figma_screenshot_url": "...", "figma_url": "https://www.figma.com/design/..." }`

### Step 6.5 — REST API (Future)

- Intention: provide a REST API that mirrors the MCP tools so UI or non-MCP clients can perform the same flows. This is planned after MCP tooling is validated in POC.
- Endpoints (mirror MCP tools):
	- `POST /api/figma/screens` — register_figma_screen (body: `screen_id, figma_file_key, figma_page_name, node_ids`)
	- `GET /api/figma/screens` (or `GET /api/figma/screens?screen_id=basket`) — get_figma_screen_config
	- `POST /api/figma/translations/{key}/figma` — update_translation_figma (body: `figma_file_key, figma_node_id`)
	- `GET /api/figma/translations/{key}` — get_figma_info (query: `market_code` optional)
- Notes: implement REST after MCP tool flows are stable; endpoints must enforce auth, rate limits, and validate `FIGMA_ACCESS_TOKEN` usage.

---

## Phase 4 — Windsurfrules Update

### Step 7 — Update `mcp_client/.windsurfrules`

#### 7a — Capability List (both API mode and Tool mode)
Add item 8 to both mode capability lists:
```
8. **Sync Figma designs** — link translation keys to Figma screen designs and fetch screenshots for BA visual review
```

#### 7b — Strict Operating Rules — Allowed Tool List
Add to the allowed tool list (rule 4):
```
- `register_figma_screen`
- `get_figma_screen_config`
- `update_translation_figma`
- `get_figma_info`
```

#### 7c — New Section: Figma Config Resolution Guard
When user requests anything Figma-related, before proceeding:
```
1. Extract screen_id from user message
2. Call get_figma_screen_config(screen_id)
	FOUND     → proceed with sync flow
	NOT FOUND → ask: "What is the Figma page name for this screen?"
					  → Search config by page_name
						 MATCH     → proceed
						 NO MATCH  → ask: "Do you have the section node IDs from Figma?
												 (right-click frame → Copy link → extract node-id)
												 Or would you like to:
												 A) Provide node IDs now → I'll save config and sync
												 B) Continue without Figma for now"
```
Never fail hard — always offer to collect config or skip.

#### 7d — New Section: Figma Sync Workflow
Step-by-step orchestration flow that Windsurf follows:
```
1. get_figma_screen_config(screen_id)
	→ get file_key + page_name + node_ids

2. Figma MCP: get_metadata(file_url pointing to section node_ids)
	→ returns subtree XML of text nodes

3. Walk text nodes in subtree
	→ match node.text → translation.default_text (scoped to screen + market)

4. For each matched node:
	→ call update_translation_figma(key, figma_file_key, figma_node_id)

5. Show BA summary table:
	| Key             | Status   | Figma Link  |
	|-----------------|----------|-------------|
	| basket.title    | synced   | [open]      |
	| basket.price    | synced   | [open]      |
	| basket.checkout | no match | —           |
```

#### 7e — Natural Language Intent Patterns
Add to inference table:

| What user says | Infer as |
|---|---|
| "sync figma for basket" / "link basket to figma" | Config Resolution Guard → Figma sync workflow |
| "show figma info for basket.title" | `get_figma_info(key="basket.title")` |
| "register basket screen in figma" | `register_figma_screen` flow |
| "what figma node is basket.title" | `get_figma_info(key="basket.title")` |

#### 7f — Tool Reference Entries
Add reference blocks for all 4 new tools following the same format as existing tools in the file.

#### 7g — Validation Rule for screen_id
Add to validation table:
```
screen_id | must be lowercase, no spaces | if not in figma_screens.json →
				trigger Config Resolution Guard, do NOT fail hard
```

---

## File Summary

| File | Action |
|---|---|
| `src/db/models.py` | Add 2 columns to `Translation` model |
| `src/config.py` | Add `FIGMA_ACCESS_TOKEN` setting |
| `src/figma_screens.json` | New — screen config (committed to git) |
| `src/ai/figma_client.py` | New — Figma REST API image fetch |
| `src/services/figma_service.py` | New — DB operations for figma fields |
| `src/mcp/tools/translation_tools.py` | Add 4 new MCP tools to `register()` |
| `mcp_client/.windsurfrules` | Update with new workflow + tools |

---

## Verification Steps

1. Run the app (`uvicorn main:app --app-dir src`) — schema auto-syncs, verify `figma_file_key` + `figma_screenshot_url` columns created on `translations` table
2. Call `register_figma_screen` via MCP with test data — verify `src/figma_screens.json` updated correctly
3. Call `get_figma_screen_config(screen_id="basket")` — verify config returned
4. Windsurf calls Figma MCP `get_metadata` on section node — verify text node subtree returned
5. Call `update_translation_figma(key="basket.title", figma_file_key=..., figma_node_id=...)` — verify screenshot URL saved in DB for all market rows
6. Call `get_figma_info(key="basket.title", market_code="IN")` — verify all figma fields + computed deep link returned
7. Test guard flow in Windsurf: ask to sync a screen not in JSON — verify assistant asks page name — asks node IDs — or offers to skip

---

## Out of Scope (POC)

- Figma webhook / auto-sync on file change
- BA review approval workflow table
- S3 / blob image storage
- Figma plugin
- Automated full-file text scanning (unreliable — replaced by manual node mapping)

---

## Phase 5 — Simplify Save Flow (one-shot Figma write)

**Status:** Planned — discovered during testing on 14 May 2026

### Problem

The original Step D called two tools sequentially:
1. `save_translations` — writes translation rows to DB
2. `update_translation_figma` — fetches screenshot from Figma REST API, then updates the already-saved rows

This is fragile: if `update_translation_figma` fails (e.g. Figma API error), translation is saved but Figma info is not. Also causes a second DB round-trip.

Additionally found a bug in `src/ai/figma_client.py` line 34: `quote(ids_param)` encodes `:` → `%3A` in the query string, which breaks the Figma Images API call for node IDs like `35773:267354`.

### Solution: fetch screenshot first, save everything in one call

#### Step 8.1 — Fix Figma API encoding bug
- File: `src/ai/figma_client.py`
- Change `ids={quote(ids_param)}` → `ids={ids_param}` (no URL-encoding of node IDs in query string)

#### Step 8.2 — New `get_figma_screenshot_url` MCP tool
- File: `src/mcp/tools/translation_tools.py`
- Add tool `get_figma_screenshot_url(figma_file_key, figma_node_id)`:
  - Calls `fetch_image_urls(figma_file_key, [figma_node_id])` directly — no DB access
  - Returns `{ figma_file_key, figma_node_id, screenshot_url }`
  - Pure Figma REST API call — fast, testable independently

#### Step 8.3 — Extend `save_translations` to accept figma fields
- File: `src/services/translation_service.py` → `save_direct_translations()`
- Read optional fields from each translation dict: `figma_file_key`, `figma_node_id`, `figma_screenshot_url`
- Write them onto the `Translation` row (both default locale row and target locale row) if present
- Fully backward-compatible — keys without figma fields save cleanly

#### Step 8.4 — New Step D in windsurfrules
Replace the 2-step save with:
```
Step i:   get_figma_screenshot_url(figma_file_key, figma_node_id)
          → returns { screenshot_url }

Step ii:  save_translations([{
            key, market_code, default_text, locale_code, value, confidence=1.0,
            figma_file_key, figma_node_id, figma_screenshot_url   ← from Step i
          }])
          → one DB write, all figma info saved atomically
```

#### Step 8.5 — update_translation_figma retained for standalone sync
- Keep `update_translation_figma` registered — still used in the "Sync Figma designs" standalone workflow
- Remove it from Step D of the Two-Step Translation Flow only
- Add `get_figma_screenshot_url` to allowed tool list in windsurfrules

### File Changes

| File | Change |
|---|---|
| `src/ai/figma_client.py` | Fix `quote(ids_param)` → `ids_param` |
| `src/mcp/tools/translation_tools.py` | Add `get_figma_screenshot_url` tool |
| `src/services/translation_service.py` | Extend `save_direct_translations` to accept + write figma fields |
| `mcp_client/.windsurfrules` | Update Step D; add `get_figma_screenshot_url` to allowed tools |

### Verification
1. Call `get_figma_screenshot_url("Fr5237RlW3syTjaBAB1kMN", "35773:267354")` → expect CDN PNG URL (confirms API bug fixed)
2. Add a key end-to-end → result table shows screenshot URL in one shot (no second tool call)
3. Check DB row — `figma_screenshot_url`, `figma_file_key`, `figma_node_id` all populated from a single `save_translations` call

