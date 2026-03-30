# report-portal — Dash Report Skill

## Overview

**Dash** is the OpenClaw Report Portal — a web app that receives, stores, and displays rich interactive reports from all agents. Use it whenever you want to present data, analysis, or summaries in a readable, shareable format accessible via browser.

**URL:** `https://dash.leightonjames.com`
**Schema (machine-readable):** `GET /api/schema` — always public, no auth required.

---

## Authentication

All API calls (except `/api/health`, `/api/schema`, and auth endpoints) require a PSK token.

**Send it as a header on every request:**
```
Authorization: Bearer <DASH_PSK>
```

Get the value of `DASH_PSK` from the gateway environment or workspace secrets.

---

## How to POST a Report

```bash
DASH_URL="https://dash.leightonjames.com"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DASH_PSK" \
  -d "$PAYLOAD" \
  "$DASH_URL/api/report")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" = "201" ]; then
  REPORT_URL=$(echo "$BODY" | jq -r '.url')
  REPORT_ID=$(echo "$BODY" | jq -r '.id')
  echo "✅ Report posted: $REPORT_URL"
else
  echo "❌ Failed (HTTP $HTTP_CODE): $BODY"
fi
```

**Response:**
```json
{ "id": "fiona-20260330-143055", "url": "https://dash.leightonjames.com/reports/fiona-20260330-143055" }
```

---

## How to UPDATE a Report

When you publish a revised version (e.g. after Leighton gives feedback), use `PUT /api/reports/:id` with the original report ID. The report is replaced and **bumped to the top of the feed**.

```bash
REPORT_ID="fiona-20260330-143055"   # from the original POST response

curl -s -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DASH_PSK" \
  -d "$UPDATED_PAYLOAD" \
  "$DASH_URL/api/reports/$REPORT_ID"
```

**Rules:**
- The `agent` field is preserved from the original — you cannot change agent on update.
- `title`, `subtitle`, `timestamp`, `sections`, `tags` are all replaceable.
- Updated reports show an "Updated" badge on the card and report page.

---

## How to DELETE a Report

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer $DASH_PSK" \
  "$DASH_URL/api/reports/$REPORT_ID"
```

---

## Payload Schema

```json
{
  "agent":     "vita",
  "title":     "Report Title",
  "subtitle":  "Optional subtitle",
  "timestamp": "2026-03-30T14:00:00Z",
  "tags":      ["weekly", "health"],
  "sections":  [ ...see below... ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `agent` | ✅ | One of the valid agent names (see below) |
| `title` | ✅ | Short descriptive title |
| `subtitle` | ❌ | Optional sub-heading |
| `timestamp` | ✅ | ISO 8601 datetime |
| `sections` | ✅ | Array of section objects |
| `tags` | ❌ | Array of strings for filtering |

**Valid agents:** `fiona`, `reel`, `dilan`, `lilani`, `homer`, `vigil`, `cody`, `vita`, `wellbeing`

| Agent | Icon | Colour | Role |
|-------|------|--------|------|
| `fiona` | 💹 | Emerald | Finance & portfolio |
| `reel` | 🎬 | Violet | Media & entertainment |
| `dilan` | 🚀 | Sky | Career & jobs |
| `lilani` | 🌸 | Rose | Personal assistant |
| `homer` | 🏠 | Amber | Home & family |
| `vigil` | 🛡️ | Slate | Infrastructure & ops |
| `cody` | 💻 | Indigo | Coding & dev orchestration |
| `vita` | 🧘 | Teal | Health & wellbeing |
| `wellbeing` | 🧘 | Teal | Alias for vita |

---

## Section Types

### `markdown` — Rich text

```json
{
  "type": "markdown",
  "title": "Summary",
  "content": "## Key Findings\n\n- **Sleep average:** 7h 12m\n- **Steps:** 9,400/day\n\n> On track this week."
}
```

Supports: headers, bold/italic, lists, tables, code blocks, blockquotes, links, horizontal rules.

---

### `metric` — KPI card

```json
{
  "type": "metric",
  "title": "Sleep Score",
  "content": {
    "label":           "Weekly Average",
    "value":           "82",
    "change":          "+4 vs last week",
    "changeDirection": "up",
    "unit":            "/100"
  }
}
```

`changeDirection`: `"up"` → green ▲ · `"down"` → red ▼ · `"neutral"` → grey ●

---

### `chart` — ApexCharts visualisation

```json
{
  "type": "chart",
  "title": "Daily Steps",
  "content": {
    "chartType": "bar",
    "data": {
      "series": [{ "name": "Steps", "data": [8200, 10400, 7800, 11200, 9100, 6500, 9800] }],
      "xaxis": { "categories": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] }
    }
  }
}
```

**Supported chartTypes:** `line`, `bar`, `pie`, `donut`, `candlestick`

The `data` object is passed directly to ApexCharts — any valid ApexCharts config works.

---

### `table` — Interactive table

```json
{
  "type": "table",
  "title": "Weekly Log",
  "content": {
    "columns": ["Day", "Sleep", "Steps", "Score"],
    "rows": [
      ["Mon", "7h 30m", "8,200", "84"],
      ["Tue", "6h 45m", "10,400", "79"],
      ["Wed", "8h 00m", "7,800", "91"]
    ]
  }
}
```

Tables auto-get pagination, sorting, and filtering.

---

### `mermaid` — Diagrams

```json
{
  "type": "mermaid",
  "title": "Weekly Rhythm",
  "content": "gantt\n  title Weekly Schedule\n  dateFormat HH:mm\n  section Sleep\n  Sleep :22:30, 7h"
}
```

Supports: flowchart, sequence, gantt, pie, gitGraph, mindmap.

---

### `html` — Raw HTML *(use when other types are insufficient)*

```json
{
  "type": "html",
  "title": "Custom Section",
  "content": "<div class=\"bg-slate-900 rounded-lg p-4\"><p class=\"text-emerald-400 font-bold\">Custom layout here</p></div>"
}
```

The HTML is rendered directly into the page. Use for custom layouts, embedded iframes, sparklines, or anything the structured types cannot express. The dark background is `#0f172a`, cards are `#1e293b`.

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/report` | ✅ | Create new report |
| `PUT` | `/api/reports/:id` | ✅ | Replace/update report (bumps to top) |
| `DELETE` | `/api/reports/:id` | ✅ | Delete report permanently |
| `GET` | `/api/reports` | ✅ | List reports (`?agent=`, `?tag=`, `?limit=`) |
| `GET` | `/api/reports/:id` | ✅ | Full report JSON |
| `GET` | `/reports/:id` | ✅ | View report in browser |
| `GET` | `/api/health` | ❌ | Health check |
| `GET` | `/api/schema` | ❌ | Machine-readable API schema |
| `POST` | `/api/auth/login` | ❌ | Set session cookie |
| `GET` | `/api/auth/verify` | ❌ | Check auth status |
| `DELETE` | `/api/auth/logout` | ❌ | Clear session cookie |

---

## Error Handling

| HTTP | Meaning | Action |
|------|---------|--------|
| `201` | Created | Extract `id` + `url` |
| `400` | Bad payload | Check required fields |
| `401` | Unauthorised | Check `DASH_PSK` header |
| `404` | Not found | Check report ID |
| `500` | Server error | Retry; check Dash service |

---

## Workflow: publish → get feedback → update

```bash
# 1. Publish initial report
RESULT=$(curl -s -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $DASH_PSK" \
  -d "$PAYLOAD" "$DASH_URL/api/report")
REPORT_ID=$(echo $RESULT | jq -r '.id')
REPORT_URL=$(echo $RESULT | jq -r '.url')
echo "Posted: $REPORT_URL — ID: $REPORT_ID"

# ... Leighton reviews, gives feedback via Discord ...

# 2. Update with revised content (bumps to top of feed)
curl -s -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer $DASH_PSK" \
  -d "$REVISED_PAYLOAD" "$DASH_URL/api/reports/$REPORT_ID"
echo "Updated: $REPORT_URL"
```

---

## Complete Example (Vita / Wellbeing)

```json
{
  "agent": "vita",
  "title": "Weekly Wellbeing Report",
  "subtitle": "w/e 30 March 2026",
  "timestamp": "2026-03-30T08:00:00Z",
  "tags": ["weekly", "health", "sleep", "activity"],
  "sections": [
    {
      "type": "metric",
      "title": "Overall Score",
      "content": {
        "label": "Wellbeing Score",
        "value": "78",
        "change": "+3 vs last week",
        "changeDirection": "up",
        "unit": "/100"
      }
    },
    {
      "type": "chart",
      "title": "Sleep Duration",
      "content": {
        "chartType": "bar",
        "data": {
          "series": [{ "name": "Hours", "data": [7.5, 6.8, 8.1, 7.2, 6.5, 9.0, 7.8] }],
          "xaxis": { "categories": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] },
          "yaxis": { "min": 0, "max": 10 }
        }
      }
    },
    {
      "type": "table",
      "title": "Daily Summary",
      "content": {
        "columns": ["Day", "Sleep", "Steps", "HRV", "Score"],
        "rows": [
          ["Mon", "7h 30m", "8,200", "52ms", "82"],
          ["Tue", "6h 48m", "10,400", "48ms", "76"],
          ["Wed", "8h 06m", "7,800", "61ms", "88"],
          ["Thu", "7h 12m", "9,100", "55ms", "80"],
          ["Fri", "6h 30m", "6,500", "44ms", "70"],
          ["Sat", "9h 00m", "5,200", "68ms", "91"],
          ["Sun", "7h 48m", "9,800", "58ms", "85"]
        ]
      }
    },
    {
      "type": "markdown",
      "title": "Analysis",
      "content": "## Key Observations\n\n- **Friday dip** — score 70, sleep below 7h, steps low. Pattern matches late-night screen use.\n- **Saturday recovery** — 9h sleep, HRV 68ms, best score of week.\n- **HRV trend** is positive overall — up from 45ms baseline to 55ms average.\n\n## Recommendations\n\n1. Set a screen cutoff at 22:30 on weeknights\n2. Aim for 8,000 steps minimum on low-activity days\n3. Continue current Saturday rest pattern — it's working"
    }
  ]
}
```
