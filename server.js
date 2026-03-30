/**
 * Dash Portal — OpenClaw Agent Report Server
 * Express app: stores and serves rich interactive reports from all agents.
 */

'use strict';

const express = require('express');
const fs      = require('fs');
const path    = require('path');

const app      = express();
const PORT     = process.env.PORT     || 3000;
const DATA_DIR = process.env.DATA_DIR || '/data/reports';
const DASH_URL = process.env.DASH_URL || `http://localhost:${PORT}`;
const DASH_PSK = process.env.DASH_PSK || '';          // empty = auth disabled

const INDEX_FILE = path.join(DATA_DIR, 'index.json');

// ── Valid agents ──────────────────────────────────────────────────────────────
const VALID_AGENTS = ['fiona', 'reel', 'dilan', 'lilani', 'homer', 'vigil', 'cody', 'vita', 'wellbeing'];

// ── Startup: ensure data directory & index exist ──────────────────────────────
function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    console.log(`[dash] Created data directory: ${DATA_DIR}`);
  }
  if (!fs.existsSync(INDEX_FILE)) {
    fs.writeFileSync(INDEX_FILE, JSON.stringify([], null, 2), 'utf8');
    console.log(`[dash] Created empty index: ${INDEX_FILE}`);
  }
}

// ── Index helpers ─────────────────────────────────────────────────────────────
function readIndex() {
  try { return JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8')); }
  catch { return []; }
}

function writeIndex(index) {
  fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2), 'utf8');
}

function buildId(agent) {
  const now  = new Date();
  const pad  = (n, w = 2) => String(n).padStart(w, '0');
  const date = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  const time = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `${agent}-${date}-${time}`;
}

// ── Auth helpers ──────────────────────────────────────────────────────────────
const COOKIE_NAME    = 'dash_psk';
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 365 days in seconds

function extractToken(req) {
  // 1. Authorization: Bearer <token>
  const auth = req.headers['authorization'] || '';
  if (auth.startsWith('Bearer ')) return auth.slice(7).trim();
  // 2. X-Dash-PSK header
  const hdr = req.headers['x-dash-psk'];
  if (hdr) return hdr.trim();
  // 3. Cookie
  const cookieHeader = req.headers['cookie'] || '';
  const match = cookieHeader.match(new RegExp(`(?:^|;)\\s*${COOKIE_NAME}=([^;]+)`));
  if (match) return decodeURIComponent(match[1]).trim();
  return null;
}

function isAuthenticated(req) {
  if (!DASH_PSK) return true;           // auth disabled
  const token = extractToken(req);
  return token === DASH_PSK;
}

// Static extensions that must always load (login page needs its own assets)
const STATIC_EXTS = /\.(js|css|ico|png|svg|woff2?|ttf|map|json)$/i;

// Paths always public regardless of PSK
const PUBLIC_PATHS = new Set([
  '/api/health',
  '/api/auth/verify',
  '/api/auth/login',
  '/api/auth/logout',
  '/api/schema',
  '/login',
]);

// ── PSK Middleware ────────────────────────────────────────────────────────────
app.use((req, res, next) => {
  if (!DASH_PSK) return next();                        // auth disabled
  if (PUBLIC_PATHS.has(req.path)) return next();       // always-public routes
  if (STATIC_EXTS.test(req.path)) return next();       // static assets

  if (isAuthenticated(req)) return next();

  // API routes → 401 JSON
  if (req.path.startsWith('/api/')) {
    return res.status(401).json({ error: 'Unauthorized — valid PSK required' });
  }

  // HTML routes → redirect to login
  res.redirect(`/login?next=${encodeURIComponent(req.path)}`);
});

// ── Middleware ─────────────────────────────────────────────────────────────────
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// ── Auth routes ───────────────────────────────────────────────────────────────

// POST /api/auth/login
app.post('/api/auth/login', (req, res) => {
  const { psk } = req.body || {};
  if (!DASH_PSK) {
    return res.json({ ok: true, message: 'Auth disabled' });
  }
  if (!psk || psk !== DASH_PSK) {
    return res.status(401).json({ ok: false, error: 'Invalid access key' });
  }
  res.setHeader('Set-Cookie',
    `${COOKIE_NAME}=${encodeURIComponent(psk)}; Max-Age=${COOKIE_MAX_AGE}; Path=/; HttpOnly; SameSite=Lax`
  );
  res.json({ ok: true });
});

// GET /api/auth/verify
app.get('/api/auth/verify', (req, res) => {
  const authEnabled = !!DASH_PSK;
  if (!authEnabled) return res.json({ authenticated: true, auth_enabled: false });
  res.json({ authenticated: isAuthenticated(req), auth_enabled: true });
});

// DELETE /api/auth/logout
app.delete('/api/auth/logout', (req, res) => {
  res.setHeader('Set-Cookie',
    `${COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`
  );
  res.json({ ok: true });
});

// ── GET /login — serve login page ─────────────────────────────────────────────
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

// ── POST /api/report — create new report ──────────────────────────────────────
app.post('/api/report', (req, res) => {
  try {
    const payload  = req.body;
    const required = ['agent', 'title', 'timestamp', 'sections'];
    for (const field of required) {
      if (!payload[field]) return res.status(400).json({ error: `Missing required field: ${field}` });
    }

    const agentKey = payload.agent.toLowerCase();
    if (!VALID_AGENTS.includes(agentKey)) {
      return res.status(400).json({ error: `Invalid agent. Must be one of: ${VALID_AGENTS.join(', ')}` });
    }

    const id         = buildId(agentKey);
    const reportPath = path.join(DATA_DIR, `${id}.json`);

    const report = {
      id,
      ...payload,
      agent:      agentKey,
      receivedAt: new Date().toISOString(),
    };

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');

    const index   = readIndex();
    const summary = {
      id,
      agent:      report.agent,
      title:      report.title,
      subtitle:   report.subtitle || null,
      timestamp:  report.timestamp,
      receivedAt: report.receivedAt,
      tags:       report.tags || [],
    };
    index.unshift(summary);
    writeIndex(index);

    const url = `${DASH_URL}/reports/${id}`;
    console.log(`[dash] New report: ${id} — ${report.title}`);
    res.status(201).json({ id, url });
  } catch (err) {
    console.error('[dash] POST /api/report error:', err);
    res.status(500).json({ error: 'Internal server error', detail: err.message });
  }
});

// ── PUT /api/reports/:id — replace/update a report (bumps to top of feed) ─────
app.put('/api/reports/:id', (req, res) => {
  try {
    const { id }     = req.params;
    const reportPath = path.join(DATA_DIR, `${id}.json`);

    if (!fs.existsSync(reportPath)) {
      return res.status(404).json({ error: 'Report not found' });
    }

    const existing = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    const payload  = req.body;

    // Merge: keep id/agent/original receivedAt; update everything else
    const updated = {
      ...existing,
      ...payload,
      id,
      agent:      existing.agent,           // agent cannot change on update
      receivedAt: existing.receivedAt,      // preserve original creation time
      updatedAt:  new Date().toISOString(),
    };

    fs.writeFileSync(reportPath, JSON.stringify(updated, null, 2), 'utf8');

    // Bump to top of index with fresh summary
    let index = readIndex();
    index     = index.filter(r => r.id !== id);
    const summary = {
      id,
      agent:      updated.agent,
      title:      updated.title,
      subtitle:   updated.subtitle || null,
      timestamp:  updated.timestamp,
      receivedAt: updated.receivedAt,
      updatedAt:  updated.updatedAt,
      tags:       updated.tags || [],
    };
    index.unshift(summary);
    writeIndex(index);

    const url = `${DASH_URL}/reports/${id}`;
    console.log(`[dash] Updated report: ${id} — ${updated.title}`);
    res.json({ id, url, updated: true });
  } catch (err) {
    console.error('[dash] PUT /api/reports/:id error:', err);
    res.status(500).json({ error: 'Internal server error', detail: err.message });
  }
});

// ── DELETE /api/reports/:id ───────────────────────────────────────────────────
app.delete('/api/reports/:id', (req, res) => {
  try {
    const { id }     = req.params;
    const reportPath = path.join(DATA_DIR, `${id}.json`);

    if (!fs.existsSync(reportPath)) {
      return res.status(404).json({ error: 'Report not found' });
    }

    fs.unlinkSync(reportPath);

    const index = readIndex().filter(r => r.id !== id);
    writeIndex(index);

    console.log(`[dash] Deleted report: ${id}`);
    res.json({ ok: true, id });
  } catch (err) {
    console.error('[dash] DELETE /api/reports/:id error:', err);
    res.status(500).json({ error: 'Internal server error', detail: err.message });
  }
});

// ── GET /api/reports ──────────────────────────────────────────────────────────
app.get('/api/reports', (req, res) => {
  try {
    const index = readIndex();
    const { agent, tag, limit } = req.query;
    let results = index;
    if (agent)  results = results.filter(r => r.agent === agent.toLowerCase());
    if (tag)    results = results.filter(r => (r.tags || []).includes(tag));
    if (limit)  results = results.slice(0, parseInt(limit, 10));
    res.json(results);
  } catch (err) {
    console.error('[dash] GET /api/reports error:', err);
    res.status(500).json({ error: 'Internal server error', detail: err.message });
  }
});

// ── GET /api/reports/:id (JSON) ───────────────────────────────────────────────
app.get('/api/reports/:id', (req, res) => {
  try {
    const reportPath = path.join(DATA_DIR, `${req.params.id}.json`);
    if (!fs.existsSync(reportPath)) return res.status(404).json({ error: 'Report not found' });
    res.json(JSON.parse(fs.readFileSync(reportPath, 'utf8')));
  } catch (err) {
    console.error('[dash] GET /api/reports/:id error:', err);
    res.status(500).json({ error: 'Internal server error', detail: err.message });
  }
});

// ── GET /reports/:id — serve report HTML page ─────────────────────────────────
app.get('/reports/:id', (req, res) => {
  const reportPath = path.join(DATA_DIR, `${req.params.id}.json`);
  if (!fs.existsSync(reportPath)) return res.status(404).send('<h1>404 — Report not found</h1>');
  res.sendFile(path.join(__dirname, 'public', 'report.html'));
});

// ── GET /api/schema — machine-readable API schema ─────────────────────────────
app.get('/api/schema', (req, res) => {
  res.json({
    version: '2.0.0',
    baseUrl: DASH_URL,
    auth: {
      enabled: !!DASH_PSK,
      methods: [
        'Authorization: Bearer <token>',
        'X-Dash-PSK: <token>',
        'Cookie: dash_psk=<token>',
      ],
      tokenLifeDays: 365,
      endpoints: {
        login:  'POST /api/auth/login',
        verify: 'GET /api/auth/verify',
        logout: 'DELETE /api/auth/logout',
      },
    },
    agents: VALID_AGENTS,
    agentMeta: {
      fiona:    { icon: '💹', color: 'emerald', description: 'Finance & portfolio' },
      reel:     { icon: '🎬', color: 'violet',  description: 'Media & entertainment' },
      dilan:    { icon: '🚀', color: 'sky',      description: 'Career & jobs' },
      lilani:   { icon: '🌸', color: 'rose',     description: 'Personal assistant' },
      homer:    { icon: '🏠', color: 'amber',    description: 'Home & family' },
      vigil:    { icon: '🛡️', color: 'slate',   description: 'Infrastructure & ops' },
      cody:     { icon: '💻', color: 'indigo',   description: 'Coding & dev orchestration' },
      vita:     { icon: '🧘', color: 'teal',     description: 'Health & wellbeing' },
      wellbeing:{ icon: '🧘', color: 'teal',     description: 'Alias for vita' },
    },
    endpoints: {
      'POST /api/report': {
        description: 'Create a new report',
        auth: true,
        body: {
          agent:     { type: 'string', required: true, enum: VALID_AGENTS },
          title:     { type: 'string', required: true },
          subtitle:  { type: 'string', required: false },
          timestamp: { type: 'string', required: true, format: 'ISO 8601' },
          tags:      { type: 'array',  required: false, items: 'string' },
          sections:  { type: 'array',  required: true,  items: 'Section' },
        },
        response: { id: 'string', url: 'string' },
      },
      'PUT /api/reports/:id': {
        description: 'Replace/update a report. Bumps to top of feed. Agent field is immutable.',
        auth: true,
        body: 'Same as POST minus agent (preserved from original)',
        response: { id: 'string', url: 'string', updated: true },
      },
      'DELETE /api/reports/:id': {
        description: 'Permanently delete a report',
        auth: true,
        response: { ok: true, id: 'string' },
      },
      'GET /api/reports': {
        description: 'List reports (newest first)',
        auth: true,
        query: { agent: 'filter by agent name', tag: 'filter by tag', limit: 'max results' },
      },
      'GET /api/reports/:id': {
        description: 'Fetch full report JSON',
        auth: true,
      },
      'GET /api/health': {
        description: 'Health check (always public)',
        auth: false,
        response: { status: 'ok', version: 'string', dashUrl: 'string' },
      },
      'GET /api/schema': {
        description: 'This schema (always public)',
        auth: false,
      },
    },
    sectionTypes: {
      markdown: {
        description: 'Rendered markdown — headers, tables, code blocks, lists',
        fields: { title: 'optional string', content: 'required markdown string' },
      },
      metric: {
        description: 'Single KPI card with value, change, and direction',
        fields: {
          title: 'optional string',
          content: {
            label:           'string',
            value:           'string or number',
            change:          'optional string',
            changeDirection: 'up | down | neutral',
            unit:            'optional string',
          },
        },
      },
      chart: {
        description: 'ApexCharts visualisation — line, bar, pie, donut, candlestick',
        fields: {
          title:   'optional string',
          content: { chartType: 'line|bar|pie|donut|candlestick', data: 'ApexCharts config object' },
        },
      },
      table: {
        description: 'Interactive DataTables table with sort, filter, pagination',
        fields: {
          title:   'optional string',
          content: { columns: 'string[]', rows: 'string[][]' },
        },
      },
      mermaid: {
        description: 'Mermaid diagram — flowchart, sequence, gantt, pie, gitGraph, mindmap',
        fields: { title: 'optional string', content: 'required mermaid diagram string' },
      },
      html: {
        description: 'Raw HTML — rendered directly. Use for custom layouts, embeds, or anything the other types cannot express.',
        fields: { title: 'optional string', content: 'required HTML string' },
        security: 'Only authenticated agents may POST reports. Raw HTML is trusted content.',
      },
    },
  });
});

// ── GET / — home page ─────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Health check ──────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', version: '2.0.0', dashUrl: DASH_URL, dataDir: DATA_DIR });
});

// ── Boot ──────────────────────────────────────────────────────────────────────
ensureDataDir();
if (!DASH_PSK) {
  console.warn('[dash] ⚠️  DASH_PSK not set — authentication disabled. Set DASH_PSK in environment to enable.');
} else {
  console.log('[dash] 🔒 PSK authentication enabled (365-day cookie)');
}
app.listen(PORT, () => {
  console.log(`[dash] 🚀 Dash Portal v2.0.0 running on port ${PORT}`);
  console.log(`[dash] 🌐 DASH_URL: ${DASH_URL}`);
  console.log(`[dash] 📁 DATA_DIR: ${DATA_DIR}`);
});

module.exports = app;
