# Martinica Docker Container - Test & Deploy Steps

## Build & Run

```bash
cd <project>/PD/Martinica

# Build and start (clean)
sudo docker compose down -v && sudo docker compose build && sudo docker compose up -d

# Start (no rebuild)
sudo docker compose up -d
```

## Access

- **URL:** http://<gateway>67:8000
- **Token:** Auto-generated on first run, retrieve with:

```bash
sudo docker exec martinica cat /home/martinica/.martinica/.token
```

## Useful Commands

```bash
# Check container status
sudo docker compose ps

# View logs (last 30 lines)
sudo docker logs martinica --tail 30

# Follow logs in real time
sudo docker logs martinica -f

# Shell into container (as martinica user)
sudo docker exec -it martinica bash

# Shell as root
sudo docker exec -it -u root martinica bash

# Check Claude Code CLI inside container
sudo docker exec martinica bash -l -c "claude --version"
```

## Stop & Clean Up

```bash
# Stop container (keeps volumes)
sudo docker compose down

# Stop and remove volumes (full reset)
sudo docker compose down -v

# Remove image too
sudo docker compose down -v --rmi all
```

## Environment Variables

Set in `docker-compose.yml` or `.env` file. Key vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Listen address |
| `APP_PORT` | `8000` | Server port |
| `APP_API_TOKEN` | (auto-generated) | Auth token for login |
| `APP_DEBUG` | `true` | Enable Swagger docs at `/docs` |
| `APP_DEFAULT_SHELL` | `/bin/bash` | Default terminal shell |
| `APP_MAX_TERMINALS` | `20` | Max concurrent terminals |

## Architecture

- **Base image:** Ubuntu 24.04
- **Runtime user:** `martinica` (non-root)
- **Python venv:** `/home/projects/Martinica/.venv`
- **Node.js:** Copied from build stage (for frontend build + npm available at runtime)
- **Frontend:** Pre-built static files served from `apps/web-server/static/`
- **Data directory:** `/home/martinica/.martinica/` (persisted via Docker volume)

## Onboarding Flow

1. Login with token
2. Onboarding wizard launches automatically
3. Install Claude Code CLI (installs Node.js via fnm if needed, then `npm install -g @anthropic-ai/claude-code`)
4. Configure OAuth: runs `claude setup-token` in embedded terminal, auto-detects token from output
5. Add a project (default browse path: `/home`)
