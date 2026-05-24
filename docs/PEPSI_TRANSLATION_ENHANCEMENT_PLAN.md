# Pepsi Translation System Enhancement Plan

## Overview
This plan outlines the database schema changes to add versioning, status workflow, feedback correction, and Figma integration to the existing Pepsi translation system with minimal disruption.

---

## Requirements

### 1. Version Info (for rollback capability)
- Track previous states of translations
- Enable rollback to previous versions
- Manual version history management (no database trigger)

### 2. Status Workflow (to identify right state)
- Default status: `PENDING_REVIEW` for new translations
- Workflow: `PENDING_REVIEW` → `APPROVED` or `REJECTED`
- BA users manage approval/rejection process
- Existing translations default to `APPROVED` (already in production)

### 3. Feedback Correction (for AI improvement)
- Market-specific corrections (not global)
- BA users provide corrections
- Manual history management (no time limit)
- Used to improve future AI translations via few-shot learning

### 4. Figma Integration
- Add nullable columns for Figma data
- NULL values acceptable initially
- Populated later (manual entry or automated sync)

---

## BEFORE (Current Schema)

### Table: `customer_uat_ind.pepsi_languages`

| Column | Type | Constraints |
|---|---|---|
| language_code | VARCHAR(10) | PRIMARY KEY |
| language | VARCHAR(100) | NOT NULL |
| created_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() |
| updated_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW(), ON UPDATE NOW() |

### Table: `customer_uat_ind.pepsi_translations`

| Column | Type | Constraints |
|---|---|---|
| id | BIGINT | PRIMARY KEY |
| label | TEXT | NOT NULL |
| language_code | VARCHAR(10) | NOT NULL, FK → pepsi_languages.language_code |
| translation | TEXT | NOT NULL |
| type | VARCHAR(255) | NULLABLE |
| created_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() |
| updated_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW(), ON UPDATE NOW() |

---

## AFTER (Proposed Schema)

### Table: `customer_uat_ind.pepsi_languages` (No Changes)

| Column | Type | Constraints |
|---|---|---|
| language_code | VARCHAR(10) | PRIMARY KEY |
| language | VARCHAR(100) | NOT NULL |
| created_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() |
| updated_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW(), ON UPDATE NOW() |

### Table: `customer_uat_ind.pepsi_translations` (Enhanced)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGINT | PRIMARY KEY | (existing) |
| label | TEXT | NOT NULL | (existing) |
| language_code | VARCHAR(10) | NOT NULL, FK → pepsi_languages.language_code | (existing) |
| translation | TEXT | NOT NULL | (existing) |
| type | VARCHAR(255) | NULLABLE | (existing) |
| created_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | (existing) |
| updated_datetime | TIMESTAMP WITH TIME ZONE | DEFAULT NOW(), ON UPDATE NOW() | (existing) |
| **status** | **VARCHAR(32)** | **NOT NULL, DEFAULT 'PENDING_REVIEW'** | **NEW** |
| **figma_node_id** | **VARCHAR(128)** | **NULLABLE** | **NEW** |
| **figma_file_key** | **VARCHAR(255)** | **NULLABLE** | **NEW** |
| **figma_screenshot_url** | **TEXT** | **NULLABLE** | **NEW** |
| **created_by** | **VARCHAR(128)** | **NULLABLE** | **NEW** |
| **updated_by** | **VARCHAR(128)** | **NULLABLE** | **NEW** |
| **version** | **BIGINT** | **NULLABLE, FK → pepsi_translation_versions.id** | **NEW** |

**Constraints Added:**
- CHECK constraint on status: `IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')`
- FK constraint on version: `REFERENCES pepsi_translation_versions(id)`

### Table: `customer_uat_ind.pepsi_translation_versions` (NEW)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGINT | PRIMARY KEY, SEQUENCE | Auto-increment |
| translation_id | BIGINT | NOT NULL, FK → pepsi_translations.id | Links to translation |
| label | TEXT | NULLABLE | Historical label |
| translation | TEXT | NULLABLE | Historical translation |
| type | VARCHAR(255) | NULLABLE | Historical type |
| status | VARCHAR(32) | NULLABLE | Historical status |
| changed_by | VARCHAR(128) | NULLABLE | Who made the change |
| change_reason | TEXT | NULLABLE | Reason for change |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When version was created |

**Indexes:**
- Index on `id`
- Index on `translation_id`

### Table: `customer_uat_ind.pepsi_feedback_corrections` (NEW)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | BIGINT | PRIMARY KEY, SEQUENCE | Auto-increment |
| translation_id | BIGINT | NULLABLE, FK → pepsi_translations.id | Links to translation (optional) |
| label | TEXT | NOT NULL | Translation key |
| language_code | VARCHAR(10) | NOT NULL | Target language |
| ai_original_value | TEXT | NULLABLE | What AI generated |
| corrected_value | TEXT | NULLABLE | Human correction |
| correction_reason | TEXT | NULLABLE | Why correction was needed |
| corrected_by | VARCHAR(128) | NULLABLE | Who provided correction |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When correction was made |

**Indexes:**
- Index on `id`
- Index on `language_code`

---

## Database Migration History

### Migration 001: Add Versioning, Status, Feedback, Figma Columns
**File:** `alembic/versions/001_add_versioning_status_feedback_figma.py`

**Changes:**
- Added `status`, `figma_node_id`, `figma_file_key`, `figma_screenshot_url`, `created_by`, `updated_by` columns to `pepsi_translations`
- Created `pepsi_translation_versions` table
- Created `pepsi_feedback_corrections` table
- Set existing translations status to `APPROVED`
- Added CHECK constraint on status values

### Migration 002: Add Sequences to New Tables
**File:** `alembic/versions/002_add_sequences_to_new_tables.py`

**Changes:**
- Created sequence `pepsi_translation_versions_id_seq` for `pepsi_translation_versions.id`
- Created sequence `pepsi_feedback_corrections_id_seq` for `pepsi_feedback_corrections.id`
- Updated `pepsi_translation_versions.id` to use sequence default
- Updated `pepsi_feedback_corrections.id` to use sequence default

### Migration 003: Add Version Column
**File:** `alembic/versions/003_add_version_column.py`

**Changes:**
- Added `version` column (BIGINT, NULLABLE) to `pepsi_translations`
- Added FK constraint: `version REFERENCES pepsi_translation_versions(id)`
- Added conditional primary key constraint to `pepsi_translation_versions.id` (if not exists)
- This allows main table to track current active version

---

## Additional Enhancements Beyond Schema

### 1. Field Consolidation: performed_by
**Before:** Separate fields `approved_by` and `rejected_by`
**After:** Single field `performed_by` for all user actions

**Impact:**
- Simplified API and service layer
- Consistent user tracking across all operations
- Updated schemas: `TranslationApproveRequest`, `TranslationRejectRequest`
- Updated service functions: `approve_translation`, `reject_translation`, `rollback_translation`
- Updated API endpoints: approve, reject, rollback
- MCP tools default `performed_by` to "system_user" for better UX

### 2. Language Code Validation
**Before:** No validation of language codes against available languages
**After:** All language codes validated against `pepsi_languages` table before translation

**Impact:**
- Prevents invalid language codes from being used
- Added `validate_language_codes()` function in `translation_service.py`
- Integrated into `ai_translate` for both single and batch operations
- Returns clear error message with list of valid codes

### 3. MCP Tools Addition
**Before:** MCP tools only covered basic CRUD operations
**After:** MCP tools include approve, reject, history, feedback, and rollback

**New MCP Tools:**
- `approve_translation` - Approve by ID or bulk by label
- `reject_translation` - Reject with optional feedback correction
- `get_translation_history` - View version history
- `get_feedback_corrections` - View feedback corrections for AI improvement
- `rollback_translation` - Revert to previous version

**Impact:**
- Full feature parity between REST API and MCP tools
- Better UX with default `performed_by` = "system_user"
- Updated windsurf rule file with new tool documentation
- All tools available in both API mode and MCP Tool mode

---

## SQLAlchemy Model Changes

### Update `PepsiTranslation` Model

```python
class PepsiTranslation(Base):
    __tablename__ = "pepsi_translations"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    
    # Existing columns
    id = Column(BigInteger, primary_key=True)
    label = Column(Text, nullable=False)
    language_code = Column(String(10), ForeignKey("customer_uat_ind.pepsi_languages.language_code"), nullable=False)
    translation = Column(Text, nullable=False)
    type = Column(String(255), nullable=True)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # New columns
    status = Column(String(32), default='PENDING_REVIEW')
    figma_node_id = Column(String(128), nullable=True)
    figma_file_key = Column(String(255), nullable=True)
    figma_screenshot_url = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)
    updated_by = Column(String(128), nullable=True)
```

### Add `PepsiTranslationVersion` Model

```python
class PepsiTranslationVersion(Base):
    __tablename__ = "pepsi_translation_versions"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    
    id = Column(BigInteger, primary_key=True)
    translation_id = Column(BigInteger, ForeignKey("customer_uat_ind.pepsi_translations.id"), nullable=False)
    label = Column(Text, nullable=True)
    translation = Column(Text, nullable=True)
    type = Column(String(255), nullable=True)
    status = Column(String(32), nullable=True)
    changed_by = Column(String(128), nullable=True)
    change_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Add `PepsiFeedbackCorrection` Model

```python
class PepsiFeedbackCorrection(Base):
    __tablename__ = "pepsi_feedback_corrections"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    
    id = Column(BigInteger, primary_key=True)
    translation_id = Column(BigInteger, ForeignKey("customer_uat_ind.pepsi_translations.id"), nullable=True)
    label = Column(Text, nullable=False)
    language_code = Column(String(10), nullable=False)
    ai_original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    correction_reason = Column(Text, nullable=True)
    corrected_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Migration Steps

### Step 0: Add Primary Key (Non-breaking)
The `pepsi_translations.id` column needs a primary key for foreign key constraints. This is handled automatically in the migration script.

### Step 1: Run Alembic Migration
**Important:** Since `alembic.ini` is in the `alembic/` directory, use the `-c` flag:

```bash
alembic -c alembic/alembic.ini upgrade head
```

This will:
- Add primary key to `pepsi_translations.id`
- Add new columns to `pepsi_translations`
- Create `pepsi_translation_versions` table
- Create `pepsi_feedback_corrections` table
- Add sequences for auto-increment on new tables

### Step 2: Verify Migration

```sql
-- Check that new columns exist in pepsi_translations
SELECT * FROM information_schema.columns 
WHERE table_name = 'pepsi_translations' 
AND table_schema = 'customer_uat_ind';

-- Check that pepsi_translation_versions table exists
SELECT * FROM information_schema.tables 
WHERE table_name = 'pepsi_translation_versions' 
AND table_schema = 'customer_uat_ind';

-- Check that pepsi_feedback_corrections table exists
SELECT * FROM information_schema.tables 
WHERE table_name = 'pepsi_feedback_corrections' 
AND table_schema = 'customer_uat_ind';
```

---

## Status Workflow

```
PENDING_REVIEW (default for new translations)
    ↓
    ├─→ APPROVED (when BA user approves)
    │
    └─→ REJECTED (when BA user rejects with correction)
```

**Status Values:**
- `PENDING_REVIEW`: Default for new translations, awaiting BA review
- `APPROVED`: Translation approved and ready for use
- `REJECTED`: Translation rejected, correction should be provided

---

## Version History Management

**Approach**: Manual table updates (no database trigger)

**Process:**
1. Before updating `pepsi_translations`, manually insert current state into `pepsi_translation_versions`
2. Update `pepsi_translations` with new values
3. Main table always contains current state
4. Version table contains historical snapshots for rollback

**Rollback Process:**
1. Query `pepsi_translation_versions` for the desired version
2. Copy that state back to `pepsi_translations`
3. Main table now has the rolled-back version

**Example Query for Rollback:**
```sql
-- Get version history for a translation
SELECT * FROM customer_uat_ind.pepsi_translation_versions 
WHERE translation_id = 123 
ORDER BY created_at DESC;

-- Restore specific version
UPDATE customer_uat_ind.pepsi_translations t
SET 
    label = v.label,
    translation = v.translation,
    type = v.type,
    status = v.status
FROM customer_uat_ind.pepsi_translation_versions v
WHERE t.id = 123 AND v.id = <desired_version_id>;
```

---

## Feedback Correction Usage

**Purpose**: Capture human corrections to improve future AI translations

**Scope**: Market-specific (corrections for India market only help India translations)

**Who Provides**: BA users

**When to Capture:**
- When status changes from `PENDING_REVIEW` → `REJECTED` with correction
- When BA users edit AI-generated translations

**AI Integration:**
```sql
-- Get recent corrections for specific language (for AI few-shot learning)
SELECT ai_original_value, corrected_value, correction_reason
FROM customer_uat_ind.pepsi_feedback_corrections
WHERE language_code = 'hi_IND'
AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Figma Integration

**Current State**: Columns added to schema (NULLABLE)

**Future Work**: Manual entry or automated sync via Figma API

**Columns:**
- `figma_node_id`: Links to specific Figma node (e.g., "35773:267354")
- `figma_file_key`: Links to Figma file (e.g., "Fr5237RlW3syTjaBAB1kMN")
- `figma_screenshot_url`: Stores screenshot reference

**Usage:**
- Link translations to specific UI elements in Figma
- Enable bi-directional sync between translations and Figma designs
- Support visual validation of translations in context

---

## Backward Compatibility

**All changes are backward compatible:**
- New columns have default values or are nullable
- Existing queries continue to work without modification
- No breaking changes to current application
- Existing translations automatically set to `APPROVED` status

---

## Testing Checklist

- [ ] Verify migration runs successfully
- [ ] Confirm existing records have status='APPROVED'
- [ ] Test new translation creation (default PENDING_REVIEW)
- [ ] Test status transitions (PENDING_REVIEW → APPROVED/REJECTED)
- [ ] Test manual version history insertion
- [ ] Test rollback from version history
- [ ] Test feedback correction creation
- [ ] Verify Figma columns accept NULL values
- [ ] Confirm existing application queries still work
- [ ] Test CHECK constraint on status values

---

## Implementation Order

1. **Update SQLAlchemy models** in `src/db/models.py`
2. **Create Alembic migration** with all SQL changes
3. **Run migration** in development environment
4. **Test** all new functionality
5. **Deploy** to production after approval

---

## Application Code Implementation Plan

### Overview

This section outlines the application code changes required to implement status workflow, version history management, and feedback correction functionality.

### Requirements Summary

1. **Status default**: If status not provided, default to `PENDING_REVIEW`
2. **Approval workflow**: BA users approve via REST API; rejection updates value and saves to feedback correction
3. **Version history**: Manual updates via code flow (not automatic)
4. **Rollback**: Deferred to later (low priority)
5. **Feedback correction**: Capture on rejection with corrected value
6. **Response fields**: Expose all new fields (status, created_by, updated_by, etc.)
7. **Status filtering**: Add status filter to list_translations; add MCP tools after testing

---

### Phase 1: Update Existing Service Functions

#### 1.1 Update `create_translation` in `translation_service.py`
- Add default status logic: if status not provided, set to `PENDING_REVIEW`
- Add support for new optional fields: `created_by`, `updated_by`
- Return new fields in response (status, created_by, updated_by)

#### 1.2 Update `update_translation` in `translation_service.py`
- Add support for updating status field
- Add support for updating audit fields (created_by, updated_by)
- Return new fields in response
- **No automatic version history** (manual only)

#### 1.3 Update `list_translations` in `translation_service.py`
- Add optional `status` parameter for filtering
- Include new fields in response (status, created_by, updated_by, figma_* fields)
- Filter by status if parameter provided

#### 1.4 Update `get_translation` in `translation_service.py`
- Include new fields in response (status, created_by, updated_by, figma_* fields)

---

### Phase 2: Add New Service Functions

#### 2.1 Add `approve_translation` function
```python
async def approve_translation(
    session,
    translation_id: int,
    approved_by: str
) -> Dict[str, Any]
```
- Updates status to `APPROVED`
- Sets `updated_by` to approver
- Returns updated translation with new fields

#### 2.2 Add `reject_translation` function
```python
async def reject_translation(
    session,
    translation_id: int,
    corrected_value: Optional[str] = None,
    correction_reason: Optional[str] = None,
    rejected_by: str
) -> Dict[str, Any]
```
- Updates status to `REJECTED`
- If corrected_value provided, updates translation value
- Creates record in `pepsi_feedback_corrections` table
- Stores ai_original_value (current value before update)
- Stores corrected_value (new value)
- Stores correction_reason and corrected_by
- Returns updated translation with new fields

#### 2.3 Add `create_version_history` function
```python
async def create_version_history(
    session,
    translation_id: int,
    changed_by: str,
    change_reason: Optional[str] = None
) -> None
```
- Manually inserts current state into `pepsi_translation_versions`
- Called explicitly in code flow when version history needed
- No automatic insertion on updates

#### 2.4 Add `get_translation_history` function
```python
async def get_translation_history(
    session,
    translation_id: int
) -> List[Dict[str, Any]]
```
- Queries `pepsi_translation_versions` for given translation_id
- Returns list of historical versions ordered by created_at DESC

#### 2.5 Add `get_feedback_corrections` function
```python
async def get_feedback_corrections(
    session,
    language_code: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]
```
- Queries `pepsi_feedback_corrections` table
- Filters by language_code if provided
- Returns recent corrections for AI few-shot learning

---

### Phase 3: Update API Schemas

#### 3.1 Update existing schemas in `api/schemas/translations.py`
- Add new fields to `TranslationResponse`: status, created_by, updated_by, figma_node_id, figma_file_key, figma_screenshot_url
- Add new fields to `TranslationCreateRequest`: status, created_by, figma_* fields (all optional)
- Add new fields to `TranslationUpdateRequest`: status, updated_by

#### 3.2 Add new schemas
- `TranslationApproveRequest`: { approved_by: str }
- `TranslationRejectRequest`: { corrected_value?: str, correction_reason?: str, rejected_by: str }
- `TranslationHistoryResponse`: { id, translation_id, label, translation, type, status, changed_by, change_reason, created_at }
- `FeedbackCorrectionResponse`: { id, translation_id, label, language_code, ai_original_value, corrected_value, correction_reason, corrected_by, created_at }

---

### Phase 4: Add REST API Endpoints

#### 4.1 Add approve endpoint
```python
@router.post("/translations/{translation_id}/approve")
async def approve_translation_endpoint(translation_id: int, request: TranslationApproveRequest)
```
- Calls `approve_translation` service function
- Returns updated translation

#### 4.2 Add reject endpoint
```python
@router.post("/translations/{translation_id}/reject")
async def reject_translation_endpoint(translation_id: int, request: TranslationRejectRequest)
```
- Calls `reject_translation` service function
- Creates feedback correction record
- Returns updated translation

#### 4.3 Add history endpoint
```python
@router.get("/translations/{translation_id}/history")
async def get_translation_history_endpoint(translation_id: int)
```
- Calls `get_translation_history` service function
- Returns list of historical versions

#### 4.4 Add feedback corrections endpoint
```python
@router.get("/feedback-corrections")
async def get_feedback_corrections_endpoint(language_code: Optional[str] = None, limit: int = 10)
```
- Calls `get_feedback_corrections` service function
- Returns list of feedback corrections

#### 4.5 Update existing endpoints
- Update `GET /translations` to accept optional `status` query parameter
- Update response models to include new fields

---

### Phase 5: Update Service Layer Imports

#### 5.1 Update `translation_service.py` imports
- Import new models: `PepsiTranslationVersion`, `PepsiFeedbackCorrection`

#### 5.2 Update `api/translations.py` imports
- Import new service functions: `approve_translation`, `reject_translation`, `create_version_history`, `get_translation_history`, `get_feedback_corrections`
- Import new schemas

---

### Phase 6: Testing (Deferred)

#### 6.1 Unit tests
- Test status default logic in create_translation
- Test approve_translation function
- Test reject_translation function with and without corrected_value
- Test feedback correction creation
- Test version history creation
- Test status filtering in list_translations

#### 6.2 Integration tests
- Test approve endpoint
- Test reject endpoint
- Test history endpoint
- Test feedback corrections endpoint
- Test status filtering via API

---

### Phase 7: MCP Tools (Deferred After Testing)

#### 7.1 Add MCP tools in `src/mcp/tools/`
- `approve_translation` tool
- `reject_translation` tool
- `get_translation_history` tool
- `get_feedback_corrections` tool
- Update existing tools to support new fields and status filtering

---

## Automatic Version History Integration

### Overview
Version history is automatically created for all translation operations (create, update, approve, reject) without requiring manual calls. This ensures complete audit trail in the pipeline.

### When Version History is Created

**Operations tracked:**
- **Create operations** - captures initial state
- **Update operations** - when content changes (translation, type, status)
- **Approve operations** - when status changes to APPROVED
- **Reject operations** - when status changes to REJECTED

**Skip conditions:**
- No actual content changes (e.g., updating to same value)
- Only audit fields changed (updated_by) without content changes

### Change Reason Auto-Generation

Change reasons are auto-generated based on operation type:
- Create: "Initial version" or "Generated by AI" (if AI-created)
- Update: "Translation updated", "Type updated", "Status updated", or combinations
- Approve: "Status changed to APPROVED"
- Reject: "Status changed to REJECTED" or "Rejected with correction"

### Implementation Changes

**Modified functions in `src/services/translation_service.py`:**

1. **`create_translation()`** - Adds version history after creating new translation (if `created_by` provided)
2. **`update_translation()`** - Adds version history before updating (skips if no content changes)
3. **`approve_translation()`** - Adds version history before approving
4. **`reject_translation()`** - Adds version history before rejecting
5. **`create_version_history()`** - Makes `change_reason` optional with auto-generation

---

## Feedback Corrections AI Integration

### Overview
Integrate feedback correction data into the AI translation pipeline to improve translation quality by providing historical correction context to the AI model.

### When to Use Feedback Corrections
- **Always** when the system translates text via LLM
- Applies to all AI translation calls (sync, async, single)
- Configurable limit (default: 10 corrections)

### Implementation Details

**1. Add Configuration Setting**
- Add `FEEDBACK_CORRECTION_LIMIT` to `src/config.py`
- Default value: 10
- Configurable via environment variable

**2. Create Service Function for AI Context**
- Create new file `src/services/feedback_service.py`
- Add `get_feedback_corrections_for_ai(session, language_code, limit)` function
- Retrieves top N most recent feedback corrections for the language
- Returns formatted string suitable for AI prompt
- Format: "Previous corrections: label 'X' was corrected from 'Y' to 'Z'"

**3. Integrate into AI Translation Pipeline**
- Modify `ai_translate` function in `src/services/translation_service.py`
- Before calling AI, retrieve feedback corrections for each target language
- Format corrections as feedback_context string
- Pass feedback_context to `generate_translations_bulk`

**4. Feedback Context Format**
The feedback_context will be appended to the system prompt as:
```
Previous corrections for {language_code}:
- Label 'basket.total' was corrected from 'टोटल' to 'कुल'
- Label 'profile.save' was corrected from 'सेव' to 'सहेजें'
```

### Files to Modify
1. `src/config.py` - Add FEEDBACK_CORRECTION_LIMIT setting
2. `src/services/feedback_service.py` - **Create new file** with feedback correction functions
3. `src/services/translation_service.py` - Import feedback_service, integrate into ai_translate
4. `src/ai/agent.py` - No changes needed (already accepts feedback_context parameter)

### Implementation Order
1. Add config setting
2. Create service function to retrieve and format corrections
3. Integrate into ai_translate (sync mode)
4. Integrate into ai_translate (async mode)
5. Test with real translations

### Benefits
- AI learns from past corrections
- Reduces repeated mistakes
- Improves translation quality over time
- Minimal overhead (configurable limit)

---

## Version Tracking and Bulk Approve Enhancements

### Overview
Add `version` column to track current version in main table, and enhance approve endpoint to support bulk approval by label.

### Implementation Details

**1. Add Version Column to Model**
- Add `version` column to `PepsiTranslation` model in `src/db/models.py`
- Type: `BigInteger`, FK to `pepsi_translation_versions.id`
- Nullable initially (existing rows won't have version history yet)

**2. Create Migration**
- Generate new migration file: `003_add_version_column.py`
- Add `version` column to `pepsi_translations` table
- Add FK constraint to `pepsi_translation_versions.id`

**3. Update create_version_history**
- After creating version entry, update main table's `version` column
- Set `translation.version = new_version.id`
- Commit both version and main table update together

**4. Enhance Approve Endpoint**
- Modify `approve_translation_endpoint` in `src/api/translations.py`
- Accept optional `label` parameter in request body
- If `label` provided:
  - Find all translations with that label
  - Approve each one with version history
  - Return all approved translations
- If `translation_id` provided (existing behavior):
  - Keep current single approval logic
- Update schema `TranslationApproveRequest` to include optional `label`

**5. Add Rollback Endpoint**
- Create `rollback_translation` function in `src/services/translation_service.py`
- Endpoint: `POST /translations/{translation_id}/rollback/{version_id}`
- Copy version data back to main table
- Create new version history entry for rollback action
- Update `version` column to point to the restored version

### Files to Modify

1. `src/db/models.py` - Add version column to PepsiTranslation
2. `alembic/versions/003_add_version_column.py` - Create migration (new file)
3. `src/services/translation_service.py` - Update create_version_history, add rollback_translation
4. `src/api/schemas/translations.py` - Add optional label to TranslationApproveRequest
5. `src/api/translations.py` - Enhance approve endpoint, add rollback endpoint

### Implementation Order

1. Add version column to model
2. Create migration file
3. Update create_version_history to set version column
4. Update approve endpoint to support bulk approve by label
5. Add rollback endpoint and function
6. Run migration
7. Test all changes

### Benefits

- Easy to see current version in main table
- Simplifies rollback operations
- Bulk approve reduces API calls
- Consistent version tracking

---

## File Changes Summary

### Files to Modify
1. `src/services/translation_service.py` - Update existing functions, add new functions, add automatic version history
2. `src/api/schemas/translations.py` - Update existing schemas, add new schemas
3. `src/api/translations.py` - Add new endpoints, update existing endpoints

### Files to Create
None (all changes in existing files)

---

## Application Code Implementation Order

1. Update service layer functions (Phase 1)
2. Add new service functions (Phase 2)
3. Update API schemas (Phase 3)
4. Add REST API endpoints (Phase 4)
5. Update imports (Phase 5)
6. Manual testing of new endpoints
7. Unit tests (Phase 6)
8. MCP tools (Phase 7)

---

## Backward Compatibility (Application Code)

- All new fields are optional in requests
- Existing endpoints continue to work without new fields
- Status defaults to PENDING_REVIEW if not provided
- New endpoints don't affect existing functionality

---

## Version Feature Rollback (Update)

**Status:** REMOVED - Versioning not required for simple translations

**Reasoning:**
- Simple translation system does not need version history
- Rollback capability adds complexity without business value
- Status workflow and feedback correction provide sufficient change tracking

**What Was Removed:**
- PepsiTranslationVersion table and model
- version column from PepsiTranslation table
- create_version_history() function and all calls
- get_translation_history() function
- rollback_translation() function
- GET /translations/{id}/history API endpoint
- POST /translations/{id}/rollback/{version_id} API endpoint
- TranslationHistoryResponse schema
- get_translation_history MCP tool
- rollback_translation MCP tool
- tests/test_version_history.py
- tests/test_rollback.py
- Related test methods in test_rest_api.py

**What Was Kept:**
- Status workflow (PENDING_REVIEW, APPROVED, REJECTED)
- Feedback correction feature
- Figma integration columns
- All other existing functionality

**PK/Sequence Clarification:**
- The enhancement plan mentioned adding a SEQUENCE to pepsi_translations.id (line 74)
- However, the actual implementation did not include this sequence
- The SQLAlchemy model only uses: `id = Column(BigInteger, primary_key=True)`
- The alembic migrations only add sequences to pepsi_translation_versions and pepsi_feedback_corrections
- No sequence was added to pepsi_translations.id in the actual code
- Therefore, no PK/sequence changes need to be removed from the codebase
