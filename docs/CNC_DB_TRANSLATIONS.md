# Translation Patterns in `cnc_db`

There are **3 distinct translation designs** in `cnc_db`, spread across ~18+ schemas
(one per country/env: `dev_ar`, `dev_cl`, `dev_co`, `dev_dr`, `dev_ec`, `dev_pe`, `ksa`,
`qa_ar`, `qa_cl`, …, `public`, shared schema `"2"`, and `customer_dev_mx`).

---

## Pattern 1 — `activity_config_translation`

**Type:** Typed-column translation table (one row per language per activity)

**Exists in:** Schema `"2"`, `public`, `dev_ar`, `dev_cl`, `dev_co`, `dev_dr`, `dev_ec`,
`dev_pe`, `ksa`, `qa_ar`, `qa_cl`, `qa_co`, `qa_dr`, `qa_ec`, `qa_pe`, `etl_test`,
`etl_test_cl`, `test_schema` — **18 schemas total**

### Schema

```sql
CREATE TABLE "2".activity_config_translation (
    id                  integer NOT NULL,         -- PK
    activity_config_id  integer,                  -- FK → activity_config(id)
    language            character varying(50),    -- locale: "es", "ar", "en", "hi"
    title               character varying(255),   -- translated title
    subtitle            character varying(255),   -- translated subtitle
    description         text,                     -- translated description
    created_at          timestamp(6) with time zone,
    created_by          character varying(50),
    updated_at          timestamp(6) with time zone,
    updated_by          character varying(50)
);
```

### FK Constraint

```sql
ALTER TABLE ONLY "2".activity_config_translation
    ADD CONSTRAINT fk128q2ghtkx270wdu7pceqtjgk
    FOREIGN KEY (activity_config_id) REFERENCES "2".activity_config(id);
```

### Entity Relationship

```
activity_config (1) ──────────────────────── (N) activity_config_translation
    id                                              activity_config_id
    name: "Daily Purchase Task"                     language: "es" / "ar" / "hi" / ...
    type: "PURCHASE"                                title: <translated>
    points: 100                                     subtitle: <translated>
                                                    description: <translated>
```

### Sample Data

**Parent — `activity_config`**

| id | name                  | type       | title              | points | application_id |
|----|-----------------------|------------|--------------------|--------|----------------|
| 10 | daily_purchase_task   | PURCHASE   | Daily Purchase     | 100    | 1              |
| 11 | weekly_checkin        | CHECKIN    | Weekly Check-in    | 50     | 1              |

**Child — `activity_config_translation`**

| id | activity_config_id | language | title                        | subtitle                  | description                                      |
|----|--------------------|----------|------------------------------|---------------------------|--------------------------------------------------|
| 1  | 10                 | en       | Daily Purchase               | Buy any product today     | Complete a purchase to earn 100 points           |
| 2  | 10                 | es       | Compra Diaria                | Compra cualquier producto | Completa una compra para ganar 100 puntos        |
| 3  | 10                 | ar       | الشراء اليومي                | اشترِ أي منتج اليوم       | أكمل عملية شراء لتكسب 100 نقطة                  |
| 4  | 10                 | hi       | दैनिक खरीदारी                 | कोई भी उत्पाद खरीदें      | 100 अंक अर्जित करने के लिए खरीदारी पूरी करें   |
| 5  | 11                 | en       | Weekly Check-in              | Check in every week       | Check in to earn 50 loyalty points               |
| 6  | 11                 | es       | Check-in Semanal             | Regístrate cada semana    | Regístrate para ganar 50 puntos de lealtad       |

### How it is consumed

The application fetches the translation for a given activity + user's preferred language:

```sql
SELECT act.name, act.type, act.points,
       tr.title, tr.subtitle, tr.description
  FROM "2".activity_config act
  LEFT JOIN "2".activity_config_translation tr
         ON tr.activity_config_id = act.id
        AND tr.language = 'es'         -- pass user's language
 WHERE act.id = 10;
```

---

## Pattern 2 — `translations` (Generic EAV)

**Type:** Entity-Attribute-Value (EAV) — generic, polymorphic

**Exists in:** Schema `"2"`, `public`, `dev_ar`, `dev_cl`, `dev_co`, `dev_dr`, `dev_ec`,
`dev_pe`, `ksa`, `qa_ar`, `qa_cl`, `qa_co`, `qa_dr`, `qa_ec`, `qa_pe`, `test_schema`,
`turkey_cep_migration` — **17 schemas total**

### Schema

```sql
CREATE TABLE "2".translations (
    id              integer NOT NULL,           -- PK
    entity_id       integer,                    -- ID of the entity being translated
    entity_type     character varying(50),      -- type: "REWARD", "BADGE", "GOAL", "TIER", etc.
    language        character varying(50),      -- locale: "es", "ar", "en", "hi"
    text_key        character varying(100),     -- which field: "title", "description", "terms"
    value_text      text,                       -- the actual translated string
    application_id  integer,                    -- tenant / app context
    created_at      timestamp(6) with time zone,
    created_by      character varying(50),
    updated_at      timestamp(6) with time zone,
    updated_by      character varying(50)
);
```

### Entity Relationship

There is **no FK constraint** at the DB level — `entity_id` / `entity_type` is a soft
polymorphic reference resolved by the application layer.

```
reward (1)          ──── (N) translations  [entity_type = "REWARD",  entity_id = reward.id]
badge (1)           ──── (N) translations  [entity_type = "BADGE",   entity_id = badge.id]
goal (1)            ──── (N) translations  [entity_type = "GOAL",    entity_id = goal.id]
tier / level (1)    ──── (N) translations  [entity_type = "TIER",    entity_id = tier.id]
... any entity ...
```

One entity + one language produces **multiple rows** (one per `text_key`):

```
entity_type="REWARD", entity_id=42, language="ar"
├── text_key="title"       → value_text = "جائزة التسوق"
├── text_key="description" → value_text = "احصل على نقاط عند كل عملية شراء"
└── text_key="terms"       → value_text = "تنطبق الشروط والأحكام"
```

### Sample Data

| id | entity_type | entity_id | language | text_key    | value_text                                        | application_id |
|----|-------------|-----------|----------|-------------|---------------------------------------------------|----------------|
| 1  | REWARD      | 42        | en       | title       | Shopping Reward                                   | 1              |
| 2  | REWARD      | 42        | en       | description | Earn points on every purchase                     | 1              |
| 3  | REWARD      | 42        | en       | terms       | Terms and conditions apply                        | 1              |
| 4  | REWARD      | 42        | es       | title       | Recompensa de Compras                             | 1              |
| 5  | REWARD      | 42        | es       | description | Gana puntos en cada compra                        | 1              |
| 6  | REWARD      | 42        | ar       | title       | جائزة التسوق                                      | 1              |
| 7  | REWARD      | 42        | ar       | description | احصل على نقاط عند كل عملية شراء                   | 1              |
| 8  | BADGE       | 7         | en       | title       | Gold Member                                       | 1              |
| 9  | BADGE       | 7         | es       | title       | Miembro de Oro                                    | 1              |
| 10 | BADGE       | 7         | ar       | title       | العضو الذهبي                                      | 1              |
| 11 | GOAL        | 15        | en       | title       | Buy 5 items this month                            | 1              |
| 12 | GOAL        | 15        | es       | title       | Compra 5 artículos este mes                       | 1              |

### How it is consumed

**Fetch all fields for one entity in one language:**

```sql
SELECT text_key, value_text
  FROM "2".translations
 WHERE entity_type = 'REWARD'
   AND entity_id   = 42
   AND language    = 'es'
   AND application_id = 1;
```

**Fetch with fallback to English when translation is missing:**

```sql
SELECT COALESCE(t_lang.value_text, t_en.value_text) AS value_text,
       t_en.text_key
  FROM "2".translations t_en
  LEFT JOIN "2".translations t_lang
         ON t_lang.entity_type    = t_en.entity_type
        AND t_lang.entity_id      = t_en.entity_id
        AND t_lang.text_key       = t_en.text_key
        AND t_lang.language       = 'ar'
 WHERE t_en.entity_type    = 'REWARD'
   AND t_en.entity_id      = 42
   AND t_en.language       = 'en'
   AND t_en.application_id = 1;
```

---

## Pattern 3 — `pepsi_translations` / `pepsi_languages` (Mexico UI strings)

**Type:** Flat label-based i18n (frontend UI strings)

**Exists in:** `customer_dev_mx` schema **only**

### Schema

```sql
-- Language registry
CREATE TABLE customer_dev_mx.pepsi_languages (
    language_code       character varying(10) NOT NULL,   -- PK: "es", "en"
    language            character varying(100) NOT NULL,  -- "Spanish", "English"
    created_datetime    timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_datetime    timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- UI string translations
CREATE TABLE customer_dev_mx.pepsi_translations (
    id                  bigint NOT NULL,                  -- PK (IDENTITY)
    label               text NOT NULL,                    -- UI key: "home.welcome_title"
    language_code       character varying(10) NOT NULL,   -- soft ref → pepsi_languages
    translation         text NOT NULL,                    -- translated string
    type                character varying(255),           -- grouping: "HOME", "REWARDS", etc.
    created_datetime    timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_datetime    timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pepsi_translations_label_language UNIQUE (label, language_code)
);
```

### Entity Relationship

```
pepsi_languages (1) ──── (N) pepsi_translations   [via language_code — soft ref, no FK]
     language_code                language_code
     "es"  Spanish                label: "home.welcome_title", translation: "Bienvenido"
     "en"  English                label: "home.welcome_title", translation: "Welcome"
```

> Note: No database-level FK from `pepsi_translations.language_code` to
> `pepsi_languages.language_code` — it's enforced by the application only.

### Sample Data

**`pepsi_languages`**

| language_code | language |
|---------------|----------|
| en            | English  |
| es            | Spanish  |

**`pepsi_translations`**

| id | label                          | language_code | translation                            | type    |
|----|--------------------------------|---------------|----------------------------------------|---------|
| 1  | home.welcome_title             | en            | Welcome to PepsiCo Rewards             | HOME    |
| 2  | home.welcome_title             | es            | Bienvenido a Recompensas PepsiCo       | HOME    |
| 3  | home.subtitle                  | en            | Earn points on every purchase          | HOME    |
| 4  | home.subtitle                  | es            | Gana puntos en cada compra             | HOME    |
| 5  | rewards.redeem_button          | en            | Redeem Now                             | REWARDS |
| 6  | rewards.redeem_button          | es            | Canjear Ahora                          | REWARDS |
| 7  | rewards.empty_state            | en            | No rewards available yet               | REWARDS |
| 8  | rewards.empty_state            | es            | No hay recompensas disponibles aún     | REWARDS |
| 9  | profile.points_label           | en            | Your Points                            | PROFILE |
| 10 | profile.points_label           | es            | Tus Puntos                             | PROFILE |

### How it is consumed

**Fetch all UI strings for a language (frontend loads at startup):**

```sql
SELECT label, translation
  FROM customer_dev_mx.pepsi_translations
 WHERE language_code = 'es'
 ORDER BY type, label;
```

**Fetch a specific key:**

```sql
SELECT translation
  FROM customer_dev_mx.pepsi_translations
 WHERE label         = 'home.welcome_title'
   AND language_code = 'es';
```

---

## Summary — All 3 Patterns Side by Side

| | `activity_config_translation` | `translations` (EAV) | `pepsi_translations` |
|---|---|---|---|
| **Scope** | Activity/task definitions | Any entity (rewards, badges, goals, tiers) | Frontend UI strings (MX only) |
| **FK** | Hard FK → `activity_config(id)` | None (soft polymorphic) | None (soft via `language_code`) |
| **Structure** | One row per language per activity | One row per language per field per entity | One row per language per label key |
| **Language column** | `language` varchar(50) | `language` varchar(50) | `language_code` varchar(10) |
| **Schemas** | 18 (all dev/qa country + shared) | 17 (all dev/qa country + shared) | `customer_dev_mx` only |
| **Unique constraint** | None | Implied by (entity_type, entity_id, language, text_key) | `(label, language_code)` |

---

## What This Means for the Translation MCP Server POC

The **EAV `translations` table** (Pattern 2) is the **primary target** — it covers rewards,
badges, goals, and tiers across every country schema. If the translation-mcp-server is going
to push approved translations back into `cnc_db`, it will write rows into this table with:

```
entity_type  = "REWARD" | "BADGE" | "GOAL" | "TIER" | ...
entity_id    = <id from cnc_db>
language     = <locale from market_locales>
text_key     = "title" | "description" | "terms" | ...
value_text   = <AI-generated or human-approved translation>
application_id = <tenant id>
```

The `activity_config_translation` table (Pattern 1) is the secondary target for when you
need to translate the activity/task definitions themselves.

`pepsi_translations` (Pattern 3) is Mexico-specific frontend i18n — a separate concern.
