# Personal AI Dashboard

[![CI](https://github.com/ebldx/dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/ebldx/dashboard/actions/workflows/ci.yml)

A self-hosted dashboard for connecting daily responsibilities with academic, career, and personal goals. It includes personal information and work management, read-only calendar imports, optional Ollama-backed briefings, explainable planning, and scheduled reviews. Features not yet implemented are intentionally shown as unavailable rather than populated with invented personal data.

> **Deployment status:** Authentication is not implemented. Run only on loopback or a trusted private network; do not expose this application publicly.

## Architecture

- `frontend/`: Next.js App Router, React, TypeScript, and Tailwind CSS.
- `backend/`: FastAPI API, Pydantic settings, SQLAlchemy 2, and Alembic.
- SQLite is the initial database. The API owns database access; the browser does not connect to SQLite.
- `docker-compose.yml` runs the web app and API on loopback and stores database files in a persistent volume.
- Calendar feeds are fetched and parsed by a backend adapter; a future authorized API can implement the same adapter contract. Calendar and AI services are not required for the application foundation to run.

See [docs/architecture.md](docs/architecture.md) for current boundaries and assumptions.

## Requirements

- Node.js 20.9 or later and npm.
- Python 3.13 or later for local backend development.
- Docker Engine and the Docker Compose plugin for container deployment.

## Local development

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Set up the backend dependencies:

   ```powershell
   cd backend
   py -3.13 -m venv .venv
   .venv\Scripts\python -m pip install -e ".[dev]"
   ```

3. Generate a calendar encryption key from `backend/`:

   ```powershell
   py -3.13 -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   ```

   Put the generated value in `CALENDAR_ENCRYPTION_KEY` in `.env`. Keep it private and backed up: calendar subscription URLs are encrypted in SQLite with this key and cannot be recovered if it is lost or rotated.
4. Apply migrations and start the API:

   ```powershell
   .venv\Scripts\alembic upgrade head
   .venv\Scripts\uvicorn app.main:app --reload
   ```

5. In a separate terminal, start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

6. Open `http://localhost:3000`. The API health check and interactive API docs are at `http://localhost:8000/api/system/health` and `http://localhost:8000/docs`.

Phase 2 includes user-maintained profile details, career and study goals, personal principles, and private PDF/DOCX CV storage with editable extraction facts. CV facts start unverified and remain suggestions until reviewed. The parser extracts text-based documents; scanned-image OCR is not included.

Phase 3 adds goal-linked projects, milestones, and user-created tasks with status, priority, deadline, effort, filtering, and search. Project progress is derived from completed milestones and tasks; it does not automatically complete a project. AI-generated task suggestions are not included.

Phase 4 accepts an authorized HTTPS iCalendar subscription URL from the calendar page. The URL is encrypted at rest with `CALENDAR_ENCRYPTION_KEY`, never returned by the API, and fetched without redirects; only public DNS destinations are allowed. Sync is manual in this phase. Events are imported separately from tasks, expanded for recurrences, and stored for 90 days in the past through 365 days ahead. The UI displays the Europe/Oslo week agenda and source timezone. No authenticated Mine studier pages are scraped and no undocumented REST API is assumed.

Phase 5 optionally connects to an operator-configured Ollama service using `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_TIMEOUT_SECONDS`. The API sends a bounded daily context (open tasks, today's calendar events, active goals and principles, and selected planning preferences); it does not send CV documents or the full profile. Briefings use a versioned prompt, schema-validated output, and a deterministic pending fallback when Ollama is unavailable or returns invalid data. One result is stored per local day; a pending result can be retried from the dashboard. The configured Ollama endpoint should be reachable only within a trusted private network. The dashboard remains usable when Ollama is not configured.

Phase 6 adds deterministic explainable task priorities, active-project recommendations, and a daily calendar analysis. Priority scores combine task priority, deadline urgency, in-progress status, and active-goal links; project scores combine importance, active-goal links, existing open work, and target dates. Up to three results are shown for each recommendation type. Calendar gaps are explicitly informational and are not treated as confirmed free time. The daily briefing prompt receives these signals as context and may add validated project suggestions without creating or changing tasks.

Phase 7 captures local feedback on daily briefings and supports user-authored preference candidates for supported planning fields. Candidates remain pending until reviewed unless the user explicitly checks the auto-apply option while entering the exact preference; this is the only auto-save rule. Applied changes store before/after snapshots, appear in preference history, and can be undone. Undo is guarded against overwriting a newer preference change. Feedback comments and pending candidates are never sent to Ollama; only the current saved profile preferences are included in briefing context.

Phase 8 adds idempotent daily briefing and completed-week review jobs, persistent retry metadata with exponential backoff, and deterministic offline review content. Weekly summaries use aggregate task, calendar, and briefing-feedback counts; feedback comments and personal profile/CV content are not included. Scheduled retry jobs revisit pending records, while the dashboard offers an immediate manual retry. Ollama remains optional.

Phase 9 adds a SQLite-aware backup command with uploaded-file snapshots, integrity manifests, verification, and local retention; a Proxmox VM deployment guide; and accessible keyboard-focus and reduced-motion behavior.

Run commands in the directory shown; backend configuration and Alembic use the backend directory as their working directory.

## Checks

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd backend
.venv\Scripts\python -m pytest
```

Run one backend test with:

```powershell
.venv\Scripts\python -m pytest tests/test_system.py::test_health_reports_database_status
```

Create or verify an application backup from `backend/`:

```powershell
.venv\Scripts\python -m app.backup ..\backups --keep 14
.venv\Scripts\python -m app.backup --verify ..\backups\daymark-backup-20261030T000000.000000Z.zip
```

Replace the example archive name with the filename printed by the backup command. Backups require a file-based SQLite database and include the database plus uploaded files. The archive is not encrypted and excludes `.env` and encryption keys; keep it in protected, encrypted off-host storage, and separately back up the calendar encryption key. See [docs/proxmox-deployment.md](docs/proxmox-deployment.md) for deployment, timers, backup verification, and recovery guidance.

## Container deployment

After creating `.env` and setting `CALENDAR_ENCRYPTION_KEY`, optionally set `OLLAMA_BASE_URL` to an Ollama endpoint reachable from the API container and `OLLAMA_MODEL` to an installed model, then run:

```sh
docker compose up --build -d
```

The initial Compose configuration binds the frontend to `127.0.0.1:3000`; the API is only reachable on the internal Compose network. Uploaded CVs are stored under the same persistent `dashboard_data` volume with private filesystem permissions. **Authentication is not implemented yet**: keep this deployment restricted to a trusted local machine and do not expose it through a network reverse proxy until authentication and HTTPS are configured. Persistent SQLite data is stored in the `dashboard_data` volume.

## Current phase

Phases 1 through 9 provide the application foundation, personal information, project/task management, iCalendar synchronization, optional Ollama daily briefings, explainable planning intelligence, reviewable preference learning, scheduled reviews, and deployment hardening. Authentication remains future work.

## Native systemd scheduling

The optional host-native scheduler is for a Linux deployment with the backend installed at `/opt/daymark`. Create a `daymark` service account, provide the backend virtual environment and `/opt/daymark/.env`, then set the host timezone to Europe/Oslo so systemd calendar timers align with the app's local day:

```sh
sudo timedatectl set-timezone Europe/Oslo
```

In `.env`, use persistent writable paths for SQLite and uploaded files:

```dotenv
DATABASE_URL=sqlite:////var/lib/daymark/dashboard.db
FILE_STORAGE_DIR=/var/lib/daymark/files
```

Apply migrations as the service account, then install and enable the timers:

```sh
sudo -u daymark sh -c 'cd /opt/daymark/backend && .venv/bin/alembic upgrade head'
sudo install -m 0644 /opt/daymark/deploy/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daymark-daily-briefing.timer daymark-daily-retry.timer daymark-weekly-review.timer daymark-weekly-retry.timer
```

The daily briefing runs at 07:00 local time; pending daily jobs are checked every 30 minutes from 07:00 through 23:30. The completed-week review runs Monday at 07:15, and pending reviews are checked at 08:15, 14:15, and 20:15 daily. Missed timer events are persisted across host downtime. To inspect timers and logs, use `systemctl list-timers 'daymark-*'` and `journalctl -u 'daymark-automation@daily-briefing.service'`. Jobs can also be started manually with `systemctl start daymark-automation@daily-briefing.service` (substitute `retry-daily`, `weekly-review`, or `retry-weekly`). The units run as `daymark` with read-only system directories; `/var/lib/daymark` is their writable state directory. These units do not run inside Docker Compose.