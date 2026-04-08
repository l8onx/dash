# Dash — Deployment Guide

## How deploys work

**Push to `main` → automatic deploy.** That's it.

The GitHub Actions pipeline (`.github/workflows/deploy.yml`) runs on the self-hosted runner on oc-vm:
1. Builds Docker image
2. Pushes to `ghcr.io/l8onx/dash:latest` + `:<sha>`
3. SSHs into docker-host (`192.168.0.50`)
4. Runs `docker compose pull && docker compose up -d`
5. Health checks `http://localhost:3000/api/health`

**Typical pipeline time: ~35 seconds.**

## VS Code tasks

`Ctrl+Shift+P` → `Tasks: Run Task`:

| Task | What it does |
|------|-------------|
| `Deploy: push to main` | Pushes current branch to main, triggers pipeline |
| `Deploy: build Docker image locally` | Local build for testing |
| `Deploy: run locally (dev)` | Starts uvicorn with hot-reload on port 3001 |
| `Deploy: health check (production)` | Checks production is healthy |
| `Deploy: view CI/CD run status` | Lists recent GitHub Actions runs |
| `Deploy: rollback` | Rolls back to a previous SHA |

## Infrastructure

| Component | Details |
|-----------|---------|
| **App host** | LXC 204 `docker-host` at `192.168.0.50` |
| **Container** | `dash-dash-1` (Docker Compose) |
| **Port** | `3000` |
| **Data** | `/opt/dash/data/` on the LXC (bind-mounted into container) |
| **Config** | `/opt/dash/.env` on the LXC |
| **Image registry** | `ghcr.io/l8onx/dash` |
| **CI runner** | Self-hosted on oc-vm (`~/actions-runner`) |

## Rollback

Every SHA is tagged and retained in GHCR. To roll back:

```bash
# On docker-host (192.168.0.50):
docker pull ghcr.io/l8onx/dash:<previous-sha>
docker tag ghcr.io/l8onx/dash:<previous-sha> ghcr.io/l8onx/dash:latest
cd /opt/dash && docker compose up -d
```

Or use the VS Code task `Deploy: rollback`.

## Environment variables

Set in `/opt/dash/.env` on the LXC:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `DATA_DIR` | `/data/reports` | Report storage path |
| `DASH_URL` | `https://dash.leightonjames.com` | Public URL used in report links |
| `DASH_PSK` | *(empty = auth disabled)* | PSK token for API auth |

## GitHub Actions secrets

Set at `github.com/l8onx/dash/settings/secrets/actions`:

| Secret | Purpose |
|--------|---------|
| `GHCR_TOKEN` | PAT with `write:packages` — push images to GHCR |
| `SSH_PRIVATE_KEY` | Deploy key for `root@192.168.0.50` |
| `LXC_HOST` | `192.168.0.50` |

## Local dev

```bash
cd ~/projects/dash
python3 -m venv /tmp/dash-venv
/tmp/dash-venv/bin/pip install -r backend/requirements.txt
DATA_DIR=/tmp/dash-data PORT=3001 DASH_URL=http://localhost:3001 \
  /tmp/dash-venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 3001
```

API docs at `http://localhost:3001/api/docs`.
