# Windsurf Rules Design for PEPSI Translation MCP Tools

This document outlines the design for the new Windsurf rules that guide the MCP Tool Assistant for the translation-mcp-server project.

## Overview

The Windsurf rules define how the MCP Tool Assistant interacts with users to manage translation keys for the India-only PEPSI translation system. The rules support two modes (API mode and Tool mode) and use the new simplified MCP tools.

## Current MCP Tools

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `list_languages` | List all available languages | None | Array of {language_code, language} |
| `get_translations` | Filter translations | language_code?, type?, label? | Array of translations |
| `create_translation` | Bulk upsert translations | Array of {label, language_code, translation, type?} | {total, created, updated, results} |
| `update_translation` | Update by ID | translation_id, translation?, type? | Updated translation object |
| `ai_translate` | AI translate bulk (auto sync/async) | Array of {label, source_text, target_language_codes, type?} | Sync: {mode, total, upserted} OR Async: {mode, batch_id, status} |
| `get_batch_status` | Check async batch status | batch_id | {status, total, completed, pending, failed, results} |

## Two Modes

### API Mode
- **Purpose:** User provides label + source text → AI API generates translations
- **Use case:** Quick translation generation using OpenAI/Ollama API tokens
- **Tools:** `ai_translate`, `get_batch_status`

### Tool Mode
- **Purpose:** User provides label + value → IDE translates (enterprise tokens) → user reviews → adds to DB
- **Use case:** Human-reviewed translations using IDE's enterprise AI tokens
- **Tools:** `create_translation`

## User Flows

### Initial Greeting Flow
1. User says "hi" or starts conversation
2. Assistant introduces itself and asks: **"A) API mode or B) Tool mode?"**
3. Wait for user to choose
4. Show capabilities for chosen mode
5. Remember mode for entire session

### API Mode Flow

**Adding translations:**
1. User provides label + source text (e.g., "add basket.total with text 'Total'")
2. Call `list_languages` to get available locales
3. Ask user: "Which locales? (default: all - en, hi_IND)"
4. Call `get_translations` with label filter to check existing keys
5. If key exists for any locale → ask "update or skip?"
6. Build array for `ai_translate`:
   ```json
   {
     "translations": [
       {"label": "basket.total", "source_text": "Total", "target_language_codes": ["en", "hi_IND"], "type": "ui"}
     ]
   }
   ```
7. Call `ai_translate`
8. If ≤10 items → sync mode (returns results immediately)
9. If >10 items → async mode (returns batch_id) → offer to poll with `get_batch_status`

**Viewing translations:**
1. Ask for filters (language_code, label, type) or show all
2. Call `get_translations` with filters
3. Display results in table format

**Updating translations:**
1. Ask for translation_id and new value
2. Call `update_translation`
3. Show updated result

### Tool Mode Flow

**Adding translations:**
1. User provides label + value (e.g., "add basket.total as 'Total' in English and 'कुल' in Hindi")
2. Call `list_languages` to get available locales
3. Ask user: "Which locales? (default: all - en, hi_IND)"
4. Call `get_translations` with label filter to check existing keys
5. If key exists for any locale → ask "update or skip?"
6. **IDE translates** the value for each locale (using enterprise AI tokens)
7. Show translations in table with confidence scores
8. Ask user to review: "Do these translations look correct?"
9. Wait for approval or corrections
10. Build array for `create_translation`:
    ```json
    {
      "translations": [
        {"label": "basket.total", "language_code": "en", "translation": "Total", "type": "ui"},
        {"label": "basket.total", "language_code": "hi_IND", "translation": "कुल", "type": "ui"}
      ]
    }
    ```
11. Call `create_translation` (upsert logic)
12. Show results (created/updated counts)

**Viewing translations:**
- Same as API mode

**Updating translations:**
- Same as API mode

## Natural Language Intent Parsing

### Key Inference
| User says | Infer label as |
|-----------|----------------|
| "total on basket" | `basket.total` |
| "save button in checkout" | `checkout.save` |
| "home in nav" | `nav.home` |

**Rules:**
- Combine screen + key name with dot: `{screen}.{key_name}`
- Lowercase only, spaces become `_`
- If screen missing → ask once

### Source Text Inference
If source text not provided, infer from key name:
- `basket.total` → "Total"
- `checkout.save_button` → "Save Button"
- Always confirm with user before proceeding

## Validation Rules

| Field | Rule | Bad | Good |
|-------|------|-----|------|
| `label` | Non-empty, dot-notation, no spaces, chars: `a-z 0-9 . _ -` | `"My Key"` | `"basket.total"` |
| `language_code` | Valid locale format | `"hindi"` | `"hi_IND"`, `"en"` |
| `translation` | Non-empty string | `""` | `"Total"` |
| `translation_id` | Positive integer | `"abc"`, `0` | `1`, `42` |
| Batch size | Max 10 per sync call | 11 items | ≤10 items |

## Workflow Steps (Strict)

1. **Understand intent** - Parse user message, infer label/source text
2. **Gather parameters** - Ask for missing required fields one at a time
3. **Validate input** - Check all validation rules before proceeding
4. **Confirm plan** - Show tool call with parameters, wait for user approval
5. **Execute** - Call the tool
6. **Next action** - Ask "What would you like to do next?"

## Strict Operating Rules

1. **Only use MCP tools** - No code, scripts, or raw SQL
2. **Never call without confirmation** - Always show plan first
3. **Ask, don't assume** - If missing info, ask for it
4. **No fabrication** - Only call real MCP tools, return actual output
5. **On failure: STOP** - Show error, ask how to proceed, never retry without confirmation
6. **Validate before calling** - Catch errors before tool call
7. **Mode persistence** - Remember chosen mode for entire session
8. **India-only** - No market selection needed (fixed to PEPSI India)

## Removed Features (from old rules)

- Approve/reject workflow
- Two-step prepare → save flow
- Market selection (now fixed to India)
- Environment selection
- Old bulk tools (add_translations_bulk_sync/async replaced by ai_translate)
- prepare_translations and save_translations (replaced by create_translation in Tool mode)

## Implementation Notes

- File location: `/Users/gaurav.siwach/Work/Gaurav/translation-mcp-server/mcp_client/.windsurfrules`
- Format: Plain text instructions for the AI assistant
- Structure: Identity → Mode selection → Workflows → Tool reference → Operating rules
- Keep similar user experience to old rules but simplified for new tools
