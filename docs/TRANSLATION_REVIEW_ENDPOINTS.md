# Translation Review Endpoints

## Approve Translation

Endpoint:

```http
POST /api/v1/translations/{id}/approve
```

Example:

```http
POST /api/v1/translations/2/approve
Content-Type: application/json
```

```json
{
  "performed_by": "reviewer@company.com",
  "reason": "translation reviewed and approved"
}
```


## Reject Translation

Endpoint:

```http
POST /api/v1/translations/{id}/reject
```

Example:

```http
POST /api/v1/translations/2/reject
Content-Type: application/json
```

```json
{
  "performed_by": "reviewer@company.com",
  "reason": "AI translation is awkward for this locale",
  "corrected_value": "सेव करें"
}
```

---

## Create Translation

Endpoint:

```http
POST /api/v1/translations
Content-Type: application/json
```

### 1) Default — single market, all locales

```json
{
  "key": "onboarding.welcome",
  "market_code": "US",
  "default_text": "Welcome",
  "performed_by": "ops@corp.com"
}
```

### 2) Override — single market, selected locales

```json
{
  "key": "profile.save",
  "market_code": "US",
  "locale_codes": ["en-US"],
  "default_text": "Save",
  "performed_by": "pm@corp.com"
}
```

### 3) Propagate — replicate to other markets

```json
{
  "key": "footer.contact",
  "market_code": "US",
  "locale_codes": ["en-US"],
  "default_text": "Contact us",
  "propagate_markets": ["EU", "APAC"],
  "performed_by": "localization@corp.com"
}
```

---

## Get Translations

Endpoint:

```http
GET /api/v1/translations
```

Query params:
- `market_code` (string) OR `market_id` (int) — one required
- `locale_code` (string, optional) — filter to a single locale
- `environment` (string, optional) — defaults to `DEV`

### Examples

All locales for a market:

```bash
curl 'http://localhost:8000/api/v1/translations?market_code=IN'
```

Filtered by locale:

```bash
curl 'http://localhost:8000/api/v1/translations?market_code=IN&locale_code=hi_IND'
```

Specific environment:

```bash
curl 'http://localhost:8000/api/v1/translations?market_code=IN&environment=PROD'
```

### Response shape

```json
[
  {
    "key": "checkout.pay_now",
    "translations": [
      {"locale_code": "en",     "value": "Pay Now",              "status": "AI_GENERATED", "version": 2, "confidence": 0.9},
      {"locale_code": "hi_IND", "value": "अभी भुगतान करें", "status": "AI_GENERATED", "version": 2, "confidence": 0.85}
    ]
  }
]
```

Returns `[]` (HTTP 200) when no translations exist for the given market/environment.

---

## Bulk Create Translations

Endpoint:

```http
POST /api/v1/translations/bulk
Content-Type: application/json
```

### 1) Minimal — keys with default text only

```json
{
  "translations": [
    {
      "key": "profile.FirstName",
      "market_code": "IN",
      "default_text": "First Name"
    },
    {
      "key": "profile.LastName",
      "market_code": "IN",
      "default_text": "Last Name"
    },
    {
      "key": "profile.Score",
      "market_code": "IN",
      "default_text": "Score"
    }
  ]
}
```

### 2) With optional context (improves AI output)

```json
{
  "translations": [
    {
      "key": "checkout.pay_now",
      "market_code": "IN",
      "default_text": "Pay Now",
      "context": "CTA button on checkout page"
    },
    {
      "key": "checkout.cancel",
      "market_code": "IN",
      "default_text": "Cancel",
      "context": "Secondary action button on checkout page"
    }
  ]
}
```

### curl example

```bash
curl -s -X POST http://localhost:8000/api/v1/translations/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "translations": [
      { "key": "profile.FirstName", "market_code": "IN", "default_text": "First Name" },
      { "key": "profile.LastName",  "market_code": "IN", "default_text": "Last Name" },
      { "key": "profile.Score",     "market_code": "IN", "default_text": "Score" }
    ]
  }'
```

### Response — 207 Multi-Status

```json
{
  "total_requested": 3,
  "total_created": 3,
  "total_failed": 0,
  "results": [
    {
      "key": "profile.FirstName",
      "market_code": "IN",
      "status": "ok",
      "created": [
        { "id": 1, "market_code": "IN", "locale_code": "hi_IND", "version": 1, "status": "AI_GENERATED" }
      ]
    },
    {
      "key": "profile.LastName",
      "market_code": "IN",
      "status": "ok",
      "created": [
        { "id": 2, "market_code": "IN", "locale_code": "hi_IND", "version": 1, "status": "AI_GENERATED" }
      ]
    },
    {
      "key": "profile.Score",
      "market_code": "IN",
      "status": "ok",
      "created": [
        { "id": 3, "market_code": "IN", "locale_code": "hi_IND", "version": 1, "status": "AI_GENERATED" }
      ]
    }
  ]
}
```
