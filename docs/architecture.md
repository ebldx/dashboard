# Architecture and assumptions

## Current implementation

This project uses a modular monolith with two deployable processes. The Next.js application serves the user interface. The FastAPI application exposes the backend API and is the only service that accesses SQLite. Alembic owns schema changes; application startup does not create tables implicitly. The container setup keeps the database on a named persistent volume and does not publish the API port to the host.

Alembic migrations establish the initial system settings, profile, career and academic goals, personal principles, original resume documents, reviewable extracted resume facts, projects, milestones, tasks, calendar sources, and imported calendar event occurrences. Personal records carry an owner identifier; the first local account uses the stable `default` identifier, allowing future authenticated accounts without redesigning record ownership. Resume binaries are stored outside SQLite in a configurable private file directory and referenced by generated storage keys.

Projects can be associated with career and academic goals. Tasks can belong to a project and one of its milestones, or be linked directly to either kind of goal. Project and milestone deletion detaches related tasks rather than deleting user-created work. Completion timestamps follow task and milestone status; project progress is a derived ratio of completed milestones and tasks and never changes the project status. Task source is explicitly user-authored in this phase.

Calendar events are imported read-only and stored separately from tasks and user-created appointments. The iCalendar adapter expands recurrence instances for a rolling window (90 days back, 365 days forward), deduplicates by source UID and recurrence identity, reconciles updates/cancellations, and preserves each event's source timezone while storing UTC instants. Europe/Oslo is used for floating iCalendar times and the calendar UI. Feed URLs are encrypted with Fernet before storage and are not returned by the API. Configure a stable `CALENDAR_ENCRYPTION_KEY`; losing or rotating it makes the saved URL unavailable. Manual sync status and errors are recorded. Fetches require HTTPS, reject non-public DNS destinations, limit feed size, disallow redirects, and do not use environment proxy settings.

`CalendarAdapter` defines the normalized snapshot contract. The current authorized personal iCalendar subscription adapter implements it; no official Mine studier REST integration has been verified, and authenticated pages are not scraped. Calendar sync remains manual.

## Planned boundaries

- Domain API routes validate requests and delegate data access and behavior to backend services.
- Calendar feeds use a backend adapter interface; imported events remain separate from user-created appointments and tasks.
- Planning priorities and project recommendations are deterministic and explainable from task priority, deadline, status, active-goal links, project importance, and target dates. Calendar analysis reports scheduled time and gaps without inferring work availability.
- AI operations use bounded selected context, a versioned prompt file, and validated Pydantic output. Daily briefing content is cached by local date; model output is not allowed to create or modify tasks or projects.
- Daily briefings and completed-week reviews are idempotently persisted. Optional systemd timers run generation and retry commands; retry attempts use capped exponential backoff and retain deterministic fallback content when Ollama is offline. Weekly review prompts receive aggregate task, calendar, and feedback counts only, never feedback comments, CV data, or full profile records.
- SQLite application backups use SQLite's online backup API and package the database with uploaded files in a private ZIP archive. Each archive has a SHA-256 manifest, a verification command, and configurable local retention; the backup excludes `.env` and encryption keys, supports SQLite only, and is not encrypted.
- Docker deployments bind the frontend to loopback and support host-mounted backup storage. Proxmox deployment guidance covers a dedicated Debian VM, Docker-compatible systemd jobs, backup verification, and recovery. Keyboard focus indicators and reduced-motion preferences are supported.
- Briefing feedback and user-entered preference candidates are kept separately from prompt context. A candidate changes profile preferences only after review, or after the user explicitly opts into immediate application for that exact value. Every applied value change records before/after history and can be undone unless a newer edit would be overwritten.
- Ollama is an optional operator-configured service, not a dependency for basic application availability. Only selected task, calendar, goal, principle, and planning-preference fields are sent; CV documents and full profile records are excluded.
- A single-user deployment is the first target. Authentication and an HTTPS reverse proxy are required before exposing the application beyond a trusted local machine.
- CV uploads accept PDF and DOCX text extraction. Extracted facts are unverified until the user reviews them; scanned-document OCR is not implemented.

## Phase 1 assumptions

- Local development uses Python 3.13+ and Node.js 20.9+.
- SQLite is the initial database. The URL is configurable for future database backends.
- The initial UI contains no personal sample data and does not imply that calendar or AI services are connected.
- Container ports bind to loopback by default. Deployment behind a reverse proxy is intentionally left to the host operator.

## Phase status

The foundation, personal information, project/task management, iCalendar integration, optional Ollama daily briefings, explainable planning intelligence, reviewable preference learning, scheduled reviews, and deployment guidance are implemented. Authentication remains future work.

## Private data boundary

The Next.js same-origin API route proxies only the implemented system, profile, goals, principles, resume, projects, tasks, calendar, and AI API groups to FastAPI. Compose keeps the API on its internal network and binds the frontend to loopback. Resume files use random storage keys and restrictive POSIX file permissions. Calendar subscription URLs are encrypted in SQLite with an operator-provided Fernet key passed through the API environment. The app does not yet authenticate users, so a private network boundary is required until authentication is implemented.
