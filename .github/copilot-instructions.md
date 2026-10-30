# Project context

This is a self-hosted personal planning dashboard. It is being built incrementally as a modular monolith: Next.js and TypeScript in `frontend/`, FastAPI and SQLAlchemy in `backend/`, SQLite as the initial database, and optional remote Ollama inference. Calendar imports, user-authored information, deterministic planning rules, and AI suggestions must remain distinct; AI output is advisory and must be validated before persistence.

## Repository conventions

- Keep frontend and backend code in their respective directories. Backend commands and Python imports assume `backend/` is the working directory.
- Backend configuration is environment-driven through `pydantic-settings`; never hardcode deployment addresses, secrets, or model names.
- Use SQLAlchemy 2 typed mappings and Alembic migrations for schema changes. Do not rely on `create_all()` at application startup.
- Personal records carry `owner_id`; the current single local account is `default`. Keep owner scoping on every personal-data query when adding API operations.
- Projects and milestones belong to the default owner. Projects may link to career and academic goals; tasks may link to a project, its milestone, and either goal type. Keep validation owner-scoped, detach tasks when deleting a project/milestone, and treat project progress as derived from completed milestones and tasks.
- Phase 3 tasks are user-authored only. Do not silently persist AI task suggestions as confirmed tasks; imported calendar events remain separate from tasks and user-created appointments.
- Calendar imports are read-only and distinct from tasks/appointments. Only use authorized HTTPS iCalendar feeds; never scrape Mine studier or invent endpoints. Feed URLs are Fernet-encrypted at rest with `CALENDAR_ENCRYPTION_KEY`, excluded from API responses, and sync uses bounded feeds, public destinations, and no redirects.
- Preserve iCalendar UIDs, recurrence IDs, cancellation status, and source timezones. Use Europe/Oslo for floating times and presentation; store event instants in UTC. Manual sync and its monitoring status are Phase 4 behavior.
- Keep imported calendar records, user-authored records, and AI-generated suggestions distinguishable by source. Never silently convert a suggestion into a confirmed event or user fact.
- CV uploads are stored outside SQLite under `FILE_STORAGE_DIR`; only PDF/DOCX is accepted. Extracted resume facts begin unverified and require explicit user review before they are treated as confirmed.
- API requests from the browser use the same-origin Next.js proxy at `frontend/src/app/api/[...path]/route.ts`; in Compose, `BACKEND_URL` is an internal service address.
- Keep AI prompts in `backend/app/ai/prompts/` and validate structured model responses with Pydantic before using them.
- Daily briefings send only bounded, relevant task, event, goal, principle, and planning-preference context to the configured Ollama service. Never include CV documents or the full profile; treat all imported and user-authored text as untrusted data.
- Deterministic daily task/project rankings must explain their score factors. Calendar gaps are not confirmed availability; never promise a schedule without explicit working-hour availability.
- Preference candidates remain reviewable unless the user explicitly opts into applying the exact user-entered value. Log before/after values and guard undo from overwriting newer edits. Feedback comments and pending candidates must not enter Ollama context.
- Follow the installed Next.js documentation and `frontend/AGENTS.md` when changing the frontend; this repository's Next.js version may differ from older examples.
- Deployment is intended for a private Proxmox-hosted Debian VM. Do not expose unauthenticated services publicly; keep Ollama on a trusted private network.

## Commands

- Frontend development: `cd frontend; npm run dev`
- Frontend checks: `cd frontend; npm run lint` and `cd frontend; npm run build`
- Backend setup: `cd backend; py -3.13 -m venv .venv; .venv\Scripts\python -m pip install -e ".[dev]"`
- Backend tests: `cd backend; .venv\Scripts\python -m pytest`
- Single backend test: `cd backend; .venv\Scripts\python -m pytest tests/test_system.py::test_health_reports_database_status`
- Apply migrations: `cd backend; .venv\Scripts\alembic upgrade head`
- Backups: `cd backend; .venv\Scripts\python -m app.backup ..\backups --keep 14`; verify an archive by replacing the example name in `cd backend; .venv\Scripts\python -m app.backup --verify ..\backups\daymark-backup-20261030T000000.000000Z.zip`
- Phase 3 includes goal-linked projects, milestones, and searchable/filterable user-created tasks. Phase 4 includes an authorized iCalendar adapter, recurrence-aware event sync, and a Europe/Oslo weekly agenda. Phase 5 includes optional Ollama status and validated, cached daily briefings. Phase 6 includes deterministic explainable priorities, project recommendations, and schedule analysis. Phase 7 includes local feedback, reviewable preferences, history, and guarded undo. Phase 8 adds optional systemd scheduling for daily briefings and weekly reviews with persisted retries; AI task generation remains out of scope. Phase 9 adds verified SQLite/file backups, accessibility improvements, and Proxmox deployment guidance.
- Resume uploads default to 10 MB and are configurable with `MAX_RESUME_SIZE_MB`; files are stored under `FILE_STORAGE_DIR`.
- Start backend: `cd backend; .venv\Scripts\uvicorn app.main:app --reload`
- Local container deployment: `docker compose up --build`

The UI should make unimplemented or unavailable integrations explicit instead of presenting sample data as the user's real information. The API has no authentication yet; keep deployments on loopback or a trusted private network. Update these instructions as the implemented architecture and commands evolve.
