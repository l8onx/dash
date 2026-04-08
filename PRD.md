# PRD: Dash — Agent Report Dashboard

## Overview
Dash is a self-hosted web app that acts as a rich reporting surface for OpenClaw agents. Agents post structured JSON data to a simple REST API; Dash renders it as beautiful, interactive, shareable reports with charts, tables, metrics, and trends. Reports are accessible via URL which agents share in Discord.

## Problem
Discord renders poorly for data-rich content — no charts, no interactive tables, limited formatting. Agents like Fiona, Sydney, and Vita produce valuable analysis that deserves a proper visual surface. Today that analysis either gets lost in chat or isn't produced at all because there's nowhere good to put it.

## Goals
- [ ] Agents can POST structured JSON reports via a simple REST API
- [ ] Reports render as rich, interactive HTML pages (charts, tables, metrics, trends)
- [ ] Each report has a stable, shareable URL
- [ ] Agents don't need to know HTML, CSS, or charting libraries — just data + schema
- [ ] Reports persist and are browsable (per-agent history)
- [ ] Works great on desktop and mobile
- [ ] Agents can edit/update or delete reports if necessary (e.g. error flagged by user)

## Non-Goals
- Not a general-purpose BI tool
- No user accounts / multi-tenancy (single household, LAN-accessible)
- Agents don't write HTML — Dash owns all presentation
- No real-time streaming (polling is fine)

## Requirements

### Functional

**FR1: Report submission API**
- `POST /api/reports` — create/update a report
- Auth: PSK (same pattern as Port4lio)
- Request body:
  ```json
  {
    "agent": "fiona",
    "title": "Weekly Portfolio Review",
    "subtitle": "Week ending 2026-04-08",
    "sections": [
      { "type": "metric", ... },
      { "type": "chart", ... },
      { "type": "table", ... },
      { "type": "text", ... }
    ]
  }
  ```
- Returns: `{ "url": "https://dash.leightonjames.com/reports/fiona/2026-04-08-weekly" }`

**FR2: Section types**

Section types are **fully compatible with the legacy Dash API** — agents using the old schema work without changes.

| Type | Description | Example |
|------|-------------|---------|
| `metric` | Single KPI with value, label, trend indicator | Portfolio value, up 2.3% |
| `metrics` | Grid of KPIs | Dashboard summary cards |
| `chart` | Line, bar, area, pie, donut, candlestick (ApexCharts) | Portfolio over time, allocation donut |
| `table` | Sortable, filterable, paginated data table | Holdings list, alerts |
| `markdown` | Markdown-rendered prose | Analysis, commentary |
| `alert` | Highlighted callout (info/warn/error) | DCA opportunity, system warning |
| `timeline` | Ordered event list | Transaction history, log events |
| `mermaid` | Diagrams (flowchart, sequence, gantt, pie, gitGraph) | Network topology, workflow |
| `html` | Raw HTML escape hatch | Custom layouts, embedded iframes |

**FR3: Report browsing**
- `GET /` — agent index (list of agents with latest report per agent)
- `GET /reports/<agent>` — all reports for that agent (reverse-chron)
- `GET /reports/<agent>/<slug>` — single report view
- `GET /reports/<agent>/latest` — always redirects to agent's most recent report

**FR4: Report persistence**
- Reports stored as JSON in SQLite
- Each report has: agent, title, subtitle, slug (auto-generated), sections, created_at, updated_at
- Same `agent` + `slug` = update in place (idempotent POST)
- Reports never auto-deleted (manual cleanup only)

**FR5: PSK authentication**
- Same middleware pattern as Port4lio
- Read (GET) is public (LAN-accessible reports)
- Write (POST) requires PSK
- PSK configured via environment variable

### Non-Functional
- **Performance:** Reports render in <500ms
- **Deployment:** Docker container, single process
- **Port:** 8002 (on shared docker-host LXC)
- **Size:** Lean — no heavy frameworks, fast cold start

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Python + FastAPI | Consistent with Port4lio, clean API |
| Frontend | React + Vite + Tailwind | Modern, consistent with Port4lio stack |
| Charts | **ApexCharts** | Legacy used it — more powerful (candlestick, compatible with legacy payloads) |
| Diagrams | Mermaid.js | Already supported in legacy, useful for network/flow diagrams |
| Database | SQLite | Zero config, single file |
| Deployment | Docker on docker-host LXC | Pattern B standard |

## Architecture

```
Agents (Fiona, Sydney, Vita, Homer...)
    → POST /api/reports (JSON data)
    ← { url: "..." }
    → Post URL to Discord

Dash (FastAPI + React)
    ├── /api/reports  — ingest + store
    ├── /              — agent index
    └── /reports/*     — report viewer (React SPA)
         ├── fetches report JSON from API
         └── renders sections using typed components
```

## Section Schema (draft)

```typescript
// Metric
{ type: "metric", label: string, value: string|number, unit?: string, trend?: "up"|"down"|"flat", trend_value?: string, color?: "green"|"red"|"amber" }

// Metrics grid
{ type: "metrics", items: Metric[] }

// Chart
{ type: "chart", chart_type: "line"|"bar"|"area"|"pie"|"donut", title?: string, data: { labels: string[], series: { name: string, values: number[] }[] } }

// Table
{ type: "table", title?: string, columns: { key: string, label: string, sortable?: boolean }[], rows: Record<string, any>[] }

// Text
{ type: "text", content: string }  // Markdown

// Alert
{ type: "alert", level: "info"|"warn"|"error", title?: string, content: string }

// Timeline
{ type: "timeline", items: { timestamp: string, label: string, detail?: string, color?: string }[] }
```

## API Endpoints

```
POST   /api/reports              — submit report (PSK required)
GET    /api/reports              — list all reports (optional ?agent= filter)
GET    /api/reports/{agent}      — list reports for agent
GET    /api/reports/{agent}/{slug} — get single report JSON
DELETE /api/reports/{agent}/{slug} — delete report (PSK required)

GET    /                         — agent index (SPA)
GET    /reports/*                — report viewer (SPA)
GET    /api/health               — health check (public)
```

## Data Model

```sql
reports
  id            INTEGER PK
  agent         TEXT NOT NULL        -- e.g. "fiona", "sydney"
  title         TEXT NOT NULL
  subtitle      TEXT
  slug          TEXT NOT NULL        -- e.g. "2026-04-08-weekly"
  sections      TEXT NOT NULL        -- JSON array
  created_at    DATETIME
  updated_at    DATETIME
  UNIQUE(agent, slug)
```

## Deployment

- **Pattern B:** Docker Compose on docker-host LXC
- **Image:** `ghcr.io/l8onx/dash:latest`
- **Port:** 8002 (internal), proxied via nginx proxy manager
- **Hostname:** `dash.leightonjames.com` (Sydney to configure)
- **Secrets:** `DASH_PSK` in `/opt/dash/.env`
- **Data:** `/opt/dash/data/dash.db` (bind-mounted volume)
- **CI/CD:** GitHub Actions — push to main → build → push to GHCR → SSH deploy

## Open Questions
- Should reports support an `expires_at` field for auto-cleanup of old agent reports?
- Do we want a simple agent index page with agent avatars/icons matching the household roster?
- Should Dash expose an OpenAPI spec so agents can self-discover the schema?

## Implementation Phases

### Phase 1 — Core (first deliverable)
1. FastAPI backend — report ingest + storage + API
2. React frontend — agent index + report viewer
3. All 7 section types rendered
4. PSK auth
5. Docker + GitHub Actions pipeline
6. Basic styling (Tailwind, clean and readable)

### Phase 2 — Polish
7. Agent avatars on index page (matching household roster)
8. Report sharing metadata (og:image, og:title for Discord unfurl)
9. Print/export to PDF
10. Report search
