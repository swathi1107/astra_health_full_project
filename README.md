# ASTRA HEALTH — Local full-stack research prototype

ASTRA HEALTH is an offline-aware astronaut health monitoring and personal-baseline decision-support prototype. It includes a FastAPI backend, SQLAlchemy persistence, a responsive HTML/CSS/JavaScript frontend, role-based access, baseline review, statistical deviation alerts, CSV/PDF reports and an application-shell service worker.

> **Important:** This is a college/research prototype, not a certified medical device. It does not diagnose, treat, or replace professional medical judgement. Sensor values in this project are manually entered/simulated unless a real integration is separately developed and validated.

## Quick start (Windows)

1. Install Python 3.10 or newer and ensure it is on PATH.
2. Extract this ZIP to a folder with write permission.
3. Double-click `START_ASTRA_HEALTH.bat`.
4. The first run creates `.venv`, installs dependencies, creates `.env`, initialises the database and seeds demonstration accounts.
5. Open `http://127.0.0.1:8000`. API docs are at `http://127.0.0.1:8000/docs`.
6. Use `STOP_ASTRA_HEALTH.bat` to stop the local server.

Default first-run database is SQLite (`astra_health.db`) so the demonstration can start without a MySQL server. The application also supports MySQL.

## Demo accounts

The seed script creates these local demonstration accounts:

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `AdminDemo123!` |
| Medical Officer | `medical` | `MedicalDemo123!` |
| Researcher | `research` | `ResearchDemo123!` |
| Astronaut | `astro` | `AstronautDemo123!` |

Change demo passwords before using the application beyond a local classroom demonstration. Do not expose this server to the public internet.

## MySQL configuration

1. Create a MySQL database, for example `astra_health`, using utf8mb4.
2. Copy `.env.example` to `.env`.
3. Set `DATABASE_URL` in `.env` to:
   `mysql+pymysql://USERNAME:PASSWORD@localhost:3306/astra_health?charset=utf8mb4`
4. Set a long random `SECRET_KEY`.
5. Ensure MySQL is running, then run `START_ASTRA_HEALTH.bat`.

The startup script runs `scripts/seed_demo.py`, which creates missing tables and demo users. It does not drop or reset existing tables. For an existing production database, use a proper reviewed migration plan before applying schema changes. SQLAlchemy `create_all` creates missing tables but does not migrate changed columns.

## Main modules

- Public landing page and login
- Role-based access: administrator, medical officer, researcher, astronaut
- Astronaut directory (create/update/deactivate endpoints)
- Mission creation and astronaut assignment endpoint
- Health reading entry and history
- Five-reading valid Earth + RESTING baseline calculation
- Baseline version history and medical approval/rejection
- Baseline-relative statistical deviation alerts
- Medical review actions and audit history
- Dashboard, trend analytics, CSV export and PDF summary
- Notifications
- Service-worker application-shell cache and online/offline indicator
- Offline reading queue endpoint (`POST /api/sync`) with client-supplied idempotency keys

## Baseline rule

Only readings with `environment=EARTH`, `activity=RESTING`, and `quality_status=VALID` count. The backend requires at least five and calculates a version from the latest five eligible readings. New baselines are `Pending` and require a medical officer or administrator to approve. Approved versions are not overwritten.

## Statistical alert rule

The demonstration rule compares a new valid reading with the latest approved baseline. For heart rate it uses the greater of 2 population standard deviations or 10% of the baseline; for other parameters it uses a 10% relative difference. Severity is a configurable research label, not a clinical classification. These thresholds are not medically validated.

## Offline limitations

The service worker caches the application shell. The API is not falsely cached as authoritative data. The sync endpoint accepts queued readings and uses `sync_key` to prevent duplicate submissions. This starter release exposes the server-side sync mechanism; a fully encrypted local health-data store and user-facing IndexedDB queue are not included. Do not use shared-device caching for sensitive health information.

## API

Interactive OpenAPI documentation: `/docs`.

Important routes:
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET/POST /api/astronauts`, `PUT/DELETE /api/astronauts/{id}`
- `GET/POST /api/missions`, `POST /api/missions/{mission_id}/assign/{astronaut_id}`
- `GET/POST /api/readings`
- `POST /api/baselines/{astronaut_id}/calculate`, `GET /api/baselines`, `POST /api/baselines/{id}/review`
- `GET /api/alerts`, `POST /api/alerts/{id}/action`
- `GET /api/analytics`, `GET /api/reports/readings.csv`, `GET /api/reports/summary.pdf`
- `POST /api/sync`
- `GET /api/admin/users`, `POST /api/admin/users`, `GET /api/admin/audit`

## Test checklist

The project is packaged with source code and setup scripts, but it has **not been executed in your Windows/MySQL environment from this chat**. After startup, verify:
1. Sign in with each demo role and confirm role restrictions.
2. Create an astronaut and a mission; assign them using the API docs.
3. Add five valid Earth RESTING readings for the same astronaut.
4. Calculate the baseline, then sign in as `medical` and approve it in Medical review.
5. Add a SPACE reading with a deviation from the approved baseline and inspect Alerts.
6. Download the PDF and CSV exports.
7. Open the app, disconnect the network and confirm the cached shell loads; reconnect and test `/api/sync` through `/docs` using a unique `sync_key`.
8. Restart the app and confirm persisted records remain.

## Project structure

```text
ASTRA_HEALTH/
  app/
    main.py
    models.py
    schemas.py
    database.py
    security.py
    static/
      index.html
      styles.css
      app.js
      sw.js
      manifest.webmanifest
  scripts/seed_demo.py
  requirements.txt
  .env.example
  START_ASTRA_HEALTH.bat
  STOP_ASTRA_HEALTH.bat
  README.md
```
