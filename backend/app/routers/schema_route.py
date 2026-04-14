from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings

router = APIRouter()

VALID_AGENTS = [
    "fiona", "reel", "dilan", "lilani", "homer", "sydney", "cody", "vita", "wellbeing",
    "clawdette", "sage", "clawmaster",
]


@router.get("/api/schema")
def get_schema():
    return JSONResponse({
        "version": "2.0.0",
        "baseUrl": settings.DASH_URL,
        "auth": {
            "enabled": bool(settings.DASH_PSK),
            "methods": [
                "Authorization: Bearer <token>",
                "X-Dash-PSK: <token>",
                "Cookie: dash_psk=<token>",
            ],
            "tokenLifeDays": 365,
            "endpoints": {
                "login":  "POST /api/auth/login",
                "verify": "GET /api/auth/verify",
                "logout": "DELETE /api/auth/logout",
            },
        },
        "agents": VALID_AGENTS,
        "agentMeta": {
            "fiona":     {"icon": "💹", "color": "emerald", "description": "Finance & portfolio"},
            "reel":      {"icon": "🎬", "color": "violet",  "description": "Media & entertainment"},
            "dilan":     {"icon": "🚀", "color": "sky",     "description": "Career & jobs"},
            "lilani":    {"icon": "🌸", "color": "rose",    "description": "Personal assistant"},
            "homer":     {"icon": "🏠", "color": "amber",   "description": "Home & family"},
            "sydney":    {"icon": "🖧",  "color": "slate",  "description": "Infrastructure & ops"},
            "clawdette": {"icon": "🧭", "color": "cyan",   "description": "Orchestrator"},
            "sage":      {"icon": "🔮", "color": "purple", "description": "Knowledge & research"},
            "clawmaster":{"icon": "🛠️", "color": "gray",   "description": "OpenClaw ops"},
            "cody":      {"icon": "💻", "color": "indigo",  "description": "Coding & dev orchestration"},
            "vita":      {"icon": "🧘", "color": "teal",    "description": "Health & wellbeing"},
            "wellbeing": {"icon": "🧘", "color": "teal",    "description": "Alias for vita"},
        },
        "endpoints": {
            "POST /api/report": {
                "description": "Create a new report",
                "auth": True,
                "body": {
                    "agent":     {"type": "string", "required": True, "enum": VALID_AGENTS},
                    "title":     {"type": "string", "required": True},
                    "subtitle":  {"type": "string", "required": False},
                    "timestamp": {"type": "string", "required": True, "format": "ISO 8601"},
                    "tags":      {"type": "array",  "required": False, "items": "string"},
                    "sections":  {"type": "array",  "required": True,  "items": "Section"},
                },
                "response": {"id": "string", "url": "string"},
            },
            "PUT /api/reports/:id": {
                "description": "Replace/update a report. Bumps to top of feed. Agent field is immutable.",
                "auth": True,
                "body": "Same as POST minus agent (preserved from original)",
                "response": {"id": "string", "url": "string", "updated": True},
            },
            "DELETE /api/reports/:id": {
                "description": "Permanently delete a report",
                "auth": True,
                "response": {"ok": True, "id": "string"},
            },
            "GET /api/reports": {
                "description": "List reports (newest first)",
                "auth": True,
                "query": {
                    "agent": "filter by agent name",
                    "tag":   "filter by tag",
                    "limit": "max results",
                },
            },
            "GET /api/reports/:id": {
                "description": "Fetch full report JSON",
                "auth": True,
            },
            "GET /api/health": {
                "description": "Health check (always public)",
                "auth": False,
                "response": {"status": "ok", "version": "string", "dashUrl": "string"},
            },
            "GET /api/schema": {
                "description": "This schema (always public)",
                "auth": False,
            },
        },
        "sectionTypes": {
            "markdown": {
                "description": "Rendered markdown — headers, tables, code blocks, lists",
                "fields": {"title": "optional string", "content": "required markdown string"},
            },
            "metric": {
                "description": "Single KPI card with value, change, and direction",
                "fields": {
                    "title": "optional string",
                    "content": {
                        "label":           "string",
                        "value":           "string or number",
                        "change":          "optional string",
                        "changeDirection": "up | down | neutral",
                        "unit":            "optional string",
                    },
                },
            },
            "chart": {
                "description": "ApexCharts visualisation — line, bar, pie, donut, candlestick",
                "fields": {
                    "title":   "optional string",
                    "content": {"chartType": "line|bar|pie|donut|candlestick", "data": "ApexCharts config object"},
                },
            },
            "table": {
                "description": "Interactive DataTables table with sort, filter, pagination",
                "fields": {
                    "title":   "optional string",
                    "content": {"columns": "string[]", "rows": "string[][]"},
                },
            },
            "mermaid": {
                "description": "Mermaid diagram — flowchart, sequence, gantt, pie, gitGraph, mindmap",
                "fields": {"title": "optional string", "content": "required mermaid diagram string"},
            },
            "html": {
                "description": "Raw HTML — rendered directly.",
                "fields": {"title": "optional string", "content": "required HTML string"},
                "security": "Only authenticated agents may POST reports. Raw HTML is trusted content.",
            },
        },
    })
