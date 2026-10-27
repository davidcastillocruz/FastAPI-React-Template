<div align="center">

# FastAPI · React Fullstack Template

**A ready-to-code development template: FastAPI backend, React frontend, PostgreSQL, Redis and Mailpit, all started with one command.**

[![CI](https://github.com/davidcastillocruz/FastAPI-React-Template/actions/workflows/ci.yml/badge.svg)](https://github.com/davidcastillocruz/FastAPI-React-Template/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite 8](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![Redis 8](https://img.shields.io/badge/Redis-8-FF4438?logo=redis&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

<img src="docs/demo.gif" alt="The example page: an email is dispatched, travels through the stack and lands on the departures board, then the page switches to the dark theme and to Spanish" width="800">

[Features](#features) · [Quick start](#quick-start) · [Project structure](#project-structure) · [Backend guide](#backend-guide) · [Frontend guide](#frontend-guide) · [Testing](#testing) · [Conventions](#conventions) · [Known limitations](#known-limitations)

</div>

---

## Overview

The template comes with the plumbing every project ends up needing (configuration, logging, translated errors, languages, themes, rate limiting, emails, tests and CI) already built, reviewed and tested, plus one complete example feature to copy from.

The example is a small demo, **"Departures from localhost"**: you write an email address, React sends it to FastAPI, PostgreSQL saves it and a styled test email arrives at Mailpit. Every request shows up on a split-flap departures board.

> [!NOTE]
> This is a **development** template. There is no production setup on purpose (no production compose, no reverse proxy, no secrets management), and there is no user or authentication module: the only feature is the demo.

## Features

### Backend

- **Validated settings** with pydantic-settings: every variable is required, a missing or wrong value stops the app on startup, and validation errors never print secret values.
- **Async database** with SQLAlchemy 2 and asyncpg, a naming convention for constraints, and **Alembic** migrations applied automatically on startup.
- **Translated errors**: every error of the API answers `{"detail": "..."}` in the user's language (404, 405, 422, 429, 500 and your own), and the OpenAPI docs show the real shape.
- **Language system**: `?lang=` > `language` cookie > `Accept-Language` > default. Translation files are checked on startup (missing languages, different keys, wrong placeholders, repeated keys).
- **Structured logging**: one line per log with a request id and the client IP, extras as `key=value`, emails masked when sending, control characters escaped, colors in the terminal. Every response carries an `X-Request-ID` header (except CORS preflights, which the CORS middleware answers before the request reaches the app).
- **Rate limiting** with slowapi, counters in Redis (with an in-memory fallback).
- **Background emails** with fastapi-mail, caught by Mailpit in development.
- **Tests** with pytest against a real PostgreSQL test database.
- **Lint and types** with ruff and pyright: modern syntax, sorted imports, trailing commas, lines up to 120 characters and type checking in standard mode, both checked in CI.

### Frontend

- **React 19 + Vite 8** in JavaScript, React Router and imports from `src` with the `@` alias.
- **Theme system**: light and dark themes as CSS variables. Follows the system live until the user picks one, saved in a cookie, applied before the first render.
- **Language system**: same languages and cookie as the backend, so the API always answers in the language of the page. `useT()` translates with named placeholders and checks every translation file in development.
- **Axios instance** with a timeout that sends the cookies, so the backend's errors arrive in the language of the page.
- **Component packages**: every page and component lives in its own folder with its JSX, CSS module, translations (when it has text of its own) and tests.
- **Tests** with Vitest, jsdom and Testing Library.

### Tooling

- **Docker Compose** for the whole stack, with hot reload in the backend and the frontend.
- **GitHub Actions**: backend tests, migrations check, lint and type check, frontend lint, tests and build on every push.

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.14, FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic, slowapi, fastapi-mail |
| Frontend | React 19, Vite 8, React Router, axios, CSS modules, oxlint |
| Services | PostgreSQL 17, Redis 8, Mailpit |
| Testing | pytest, pytest-asyncio, httpx · Vitest, jsdom, Testing Library |
| Tooling | Docker Compose, GitHub Actions, ruff, pyright |

## Quick start

**Requirements:** [Docker](https://www.docker.com/) with Docker Compose. Everything, tests included, runs inside the containers.

```bash
git clone https://github.com/davidcastillocruz/FastAPI-React-Template.git
cd FastAPI-React-Template

cp backend/.env.api.example backend/.env.api
cp backend/.env.db.example backend/.env.db

docker compose up --build
```

Then open:

| Service | URL |
| --- | --- |
| Web | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs |
| Mailpit (sent emails) | http://localhost:8025 |
| PostgreSQL (from a database client) | `localhost:5433` |

Open the web at `localhost`, not `127.0.0.1`: `localhost:5173` is the origin allowed in `CORS_ORIGINS`, from any other one every call to the API is blocked.

Saving a Python file in `backend/src` reloads the API, and saving a file in `frontend/src` updates the page (Vite's hot reload). The backend's translation files are only read on startup: after changing one, run `docker compose restart backend`. The migrations run every time the backend starts.

## Project structure

```
.
├── backend/
│   ├── src/
│   │   ├── main.py              # app, request logging middleware, CORS, routers
│   │   ├── core/                # settings, logger, request context, languages, errors, limiter, shared translations
│   │   ├── api/                 # dependencies (Language, client IP) and one router per module
│   │   ├── modules/             # features: models, schemas, repositories, services, translations
│   │   ├── mail/
│   │   │   ├── sender.py        # send_email, run in the background
│   │   │   └── templates/       # one folder per email: its template and its translations
│   │   ├── database/
│   │   │   ├── base.py          # Base, with the naming convention of constraints
│   │   │   ├── session.py       # async engine, get_db, DbSession
│   │   │   └── models.py        # imports every model for SQLAlchemy and Alembic
│   │   └── shared/schemas.py    # MessageResponse {message}, ErrorResponse {detail}
│   ├── alembic/                 # env.py and the migration template
│   │   └── versions/            # one file per migration
│   ├── tests/
│   ├── ruff.toml                # lint rules
│   └── pyrightconfig.json       # type checker settings
├── frontend/
│   └── src/
│       ├── main.jsx             # providers and every route
│       ├── index.css            # global styles
│       ├── themes/              # theme variables, provider and useTheme
│       ├── languages/           # language provider, useLanguage and useT
│       ├── utils/               # api (axios) and cookies
│       ├── pages/               # one folder per page
│       ├── components/          # one folder per shared component
│       ├── hooks/               # shared hooks
│       ├── features/            # big features with their own pages, components and hooks
│       └── test/                # setup of the frontend tests
├── docs/                    # the GIF of this README
├── LICENSE
├── .github/workflows/ci.yml
└── docker-compose.yml
```

Folders that only hold a `.gitkeep` (`frontend/src/hooks/`, `frontend/src/features/`, `backend/alembic/versions/` before the first migration) are part of the structure on purpose: they are where that code goes once it exists.

## Backend guide

### Adding a module

Each feature is a module in `backend/src/modules/<module>/`, split in layers. Use `modules/demo/` as the reference. A request goes router → service → repository: the repository only talks to the database and returns ORM models, the service holds the logic, raises the `HTTPException`s and returns Pydantic schemas, and the router returns what the service gives.

1. **Model** in `models/`, inheriting from `Base` (`src/database/base.py`), then import it in `src/database/models.py`. Without that import Alembic doesn't see the table and `--autogenerate` creates an empty migration. Class names are singular (`EmailRequest`), table names plural (`email_requests`).
2. **Migration**: generate it, review the file in `alembic/versions/` and apply it with `docker compose restart backend` (the hot reload doesn't run the migrations).
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "create users"
   ```
   On Linux with Docker Engine the container creates the file as root, so you can't edit it without `sudo`. Run it as your user instead (Docker Desktop on macOS and Windows doesn't need it):
   ```bash
   docker compose exec -u "$(id -u):$(id -g)" backend alembic revision --autogenerate -m "create users"
   ```
3. **Schemas** in `schemas/`: what the endpoints receive and return.
4. **Repository** in `repositories/`: only database queries, no `try/except` (closing the session rolls back).
5. **Service** in `services/`: the logic. Catch only foreseeable errors and turn them into an `HTTPException`, the rest becomes a translated 500.
6. **Translations** in `translations/<name>_translations.json`: every `translations/*_translations.json` inside `src/` is loaded on startup, and a broken one stops the backend (see below).
7. **Router** in `src/api/routers/`, included in `main.py`.
8. **Tests** in `backend/tests/`.

### Errors and translations

Translation files hold every text in every language, with `%s` placeholders:

```json
{
  "USER_NOT_FOUND": {
    "en": { "detail": "User %s doesn't exist" },
    "es": { "detail": "El usuario %s no existe" }
  }
}
```

```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=get_error_detail("USER_NOT_FOUND", language, {"detail": (username,)}),
)
```

Successful responses that only carry a message use `MessageResponse` (`{"message": "..."}`), and every error answers `{"detail": "..."}`. When the same error is raised in several places, a helper builds and returns the `HTTPException` and the call site raises it (see `_already_requested` in the demo service).

The backend refuses to start when a translation file is invalid JSON, repeats a key or a response name, misses a language of `AVAILABLE_LANGUAGES`, has different text keys or a different number of `%s` in each language, or has a literal `%` next to a `%s` (write it `%%`). The log line of the error names the file and the entry.

### Logging

```python
logger = logging.getLogger(__name__)
logger.info("User created", extra={"user_id": user.id})
```

The request id and the client IP are added to every line automatically. Keep the message fixed, put the data in `extra`, and never log personal data.

### Configuration

Every setting lives in `src/core/settings.py` and is **required**. A new setting goes in `Settings`, in `backend/.env.api` (or `backend/.env.db` if PostgreSQL uses it too) and in its `.example`, and in `VALID` in `backend/tests/test_settings.py`: the settings tests ignore the `.env` files and only use the values listed there.

Docker reads the `.env` files only when it creates the containers: after changing a value, run `docker compose up -d` (a restart keeps the old values). The `POSTGRES_*` values only create the user and the database the first time; to change them later, run `docker compose down -v`, which deletes the data of the database.

## Frontend guide

### Adding a page or a component

Every page and component is a folder with everything it needs:

```
pages/ProfilePage/
├── ProfilePage.jsx
├── ProfilePageStyle.module.css
├── ProfilePageTranslation.json   # only if it has text of its own
└── ProfilePage.test.jsx
```

Pages are registered in `src/main.jsx`:

```jsx
const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/profile', element: <ProfilePage /> },
  { path: '*', element: <NotFoundPage /> },
]);
```

Keep the `*` route: it shows `NotFoundPage` for any other path.

### Translations

```json
{ "greeting": { "en": "Hello {name}", "es": "Hola {name}" } }
```

```jsx
import { useT } from '@/languages/useT';

import translations from './ProfilePageTranslation.json';

const t = useT(translations);
t('greeting', { name: 'Ana' });
```

`const { language, setLanguage } = useLanguage()` reads or changes the language without reloading the page.

To add a language, add it to `AVAILABLE_LANGUAGES` in `backend/.env.api` and its `.example`, to `LANGUAGES` in `frontend/src/languages/languages.js`, and to every translation file of the backend and the frontend (the backend doesn't start while one is missing it). Keep `MAIN_LANGUAGE` the same on both sides.

### Themes

The variables of `src/themes/themes.css` work in any CSS module without importing anything:

```css
.card {
  background: var(--color-surface);
  color: var(--color-text);
}
```

`const { theme, setTheme } = useTheme()` reads or changes the theme. A new variable goes in both themes.

### Calling the API

```js
import { api } from '@/utils/api';

try {
  const { data } = await api.post('/users', { email });
} catch (error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') {
    // The backend's message, already translated
    setError(detail);
  } else {
    // An answer without a detail (a proxy's error page...) or no answer at all (backend down, timeout)
    setError(t(error.response ? 'unexpected' : 'noConnection'));
  }
}
```

## Testing

```bash
docker compose exec backend pytest     # backend, against its own test database
docker compose exec frontend npm test  # frontend
```

The backend also has a linter and a type checker, the same ones CI runs:

```bash
docker compose exec backend ruff check        # lint (ruff check --fix fixes most of it)
docker compose exec backend pyright           # types
```

### Without Docker

The tests also run on your computer, the same way CI runs them. The backend needs Python 3.14, the `.env` files of the quick start and the `db` container (or any PostgreSQL) running; the frontend needs Node 24.

```bash
cd backend
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_HOST=localhost DATABASE_PORT=5433 pytest
ruff check . && pyright
```

```bash
cd frontend
npm ci
npm test && npm run lint && npm run build
```

The backend tests create and use an `app_test` database in the same PostgreSQL, so your development data is never touched. `docker compose exec frontend npx vitest` keeps the frontend tests running while you code.

The backend tests always run with `en` as the main language and `en`, `es` available (forced in `tests/conftest.py`), whatever your `.env.api` says. The frontend's language tests follow `MAIN_LANGUAGE` and `LANGUAGES` of `src/languages/languages.js`.

### Continuous integration

On every push and pull request, GitHub Actions runs three jobs in parallel:

- **Backend tests**: `alembic upgrade head` and `alembic check` (a model changed without its migration fails), then pytest against a PostgreSQL 17 service.
- **Backend lint and types**: ruff with the rules of `backend/ruff.toml` and pyright with `backend/pyrightconfig.json`.
- **Frontend**: oxlint, Vitest and the production build.

## Useful commands

| Task | Command |
| --- | --- |
| Start everything | `docker compose up --build` |
| Stop everything | `docker compose down` |
| Backend logs | `docker compose logs -f backend` |
| New migration | `docker compose exec backend alembic revision --autogenerate -m "..."` (on Linux with Docker Engine, add `-u "$(id -u):$(id -g)"` after `exec`) |
| Apply the migrations | `docker compose restart backend` |
| Undo the last migration | `docker compose exec backend alembic downgrade -1` (then delete or edit its file in `alembic/versions/`: the backend runs `alembic upgrade head` every time it starts) |
| Add a frontend dependency | `docker compose exec frontend npm install <package>` |
| Reinstall the frontend dependencies of the container (after a pull that changes `package.json`) | `docker compose up --build -V` |
| Lint the backend | `docker compose exec backend ruff check` (add `--fix` to fix it) |
| Type check the backend | `docker compose exec backend pyright` |
| Lint the frontend | `docker compose exec frontend npm run lint` |

## Conventions

- **Language**: code, comments and commit messages in English; texts for the user in the translation files (`*_translations.json` in the backend, `*Translation.json` in the frontend), with the same keys and placeholders in every language and the Spanish texts addressing the user as "tú". The only texts outside them are names like FastAPI or React and the English title and description of `index.html`, shown before the JavaScript loads.
- **Names**: backend files in `snake_case`, one per concept (`email_request_repository.py`), modules in singular (`modules/demo/`). Frontend components and pages in a `PascalCase` folder with `Name.jsx`, `NameStyle.module.css`, `NameTranslation.json` and `Name.test.jsx`; systems and utilities in `camelCase` (`themes/`, `languages/`, `cookies.js`).
- **Imports, backend**: standard library, third party, then `src`, one blank line between groups. ruff (`I` rules) enforces it.
- **Imports, frontend**: packages (alphabetically, so `axios` goes before `react`), then `@/` imports, then relative ones (in a component, `./NameStyle.module.css` and `./NameTranslation.json`), one blank line between groups.
- **Format**: backend with double quotes, trailing commas and 120 characters per line (ruff); frontend with single quotes. There is no formatter, follow the surrounding code.
- **Comments**: above the line they explain, saying why rather than what, descriptive and without first person. No commented-out code and no `TODO` without context.
- **CSS**: colors from the variables of `themes.css` (only neutral shadows, highlights and the edge of the dark board are written as `rgb()` or `white`), one CSS module per component, `clamp()` for fluid sizes (headings, page spacing), `px` for the rest of the text.
- **Ignores**: every `# noqa`, `# pyright: ignore[...]` and `// oxlint-disable-next-line` in the code is needed (each one was checked by removing it and running the tool). Remove one only after checking that the tool stays green without it.

## Known limitations

- **Localhost URLs in the frontend**: the API URL (`src/utils/api.js`) and the Mailpit link (`src/pages/HomePage/HomePage.jsx`) are written as `http://localhost:8000` and `http://localhost:8025`. Opening the web from another host needs both changed, and that host added to `CORS_ORIGINS`.
- **Rate limit per IP**: the limit is per client IP as the backend sees it. Behind a reverse proxy every user would share the proxy's IP, and in Docker every request from your computer arrives from the gateway of the Docker network (like `172.18.0.1`), so all your browser tabs share one counter.
- **Offset pagination**: a request saved between two page loads moves the next page one row, so a row can show twice. The order itself is stable (newest first, ties broken by id).
- **Translation files are read on startup**: a change needs `docker compose restart backend`.
- **Dependency audit** (2026-10-27): `npm audit` reports nothing. `pip-audit -r requirements.txt` reports `certifi 2026.7.22` (PYSEC-2026-4320, fixed in 2026.10.18) and `opentelemetry-api 1.45.0` (CVE-2026-114603, fixed in 1.45.1). The pinned versions were not changed: updating them is a decision for whoever uses the template.
- **slowapi on Python 3.14**: pytest shows a `DeprecationWarning` from slowapi (`asyncio.iscoroutinefunction`). It comes from the library and doesn't affect the app until Python 3.16.

## License

[MIT](LICENSE): use it, change it and ship it, keeping the copyright notice.

---

<div align="center">

Made by [@davidcastillocruz](https://github.com/davidcastillocruz)

</div>
