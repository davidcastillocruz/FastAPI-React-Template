# FastAPI-React-Template

Full-stack base to clone and build on: FastAPI (async SQLAlchemy, Alembic, PostgreSQL, Redis rate limiting, email) and React + Vite, all in Docker. The only feature is a demo, `modules/demo/`: it is the reference for every new module, and it is removed when a real project starts (see the README, *Starting a project*).

This file says how to work on the template and on anything built from it. The README has the setup and the guides for people.

## Rule number one: don't invent style

**The code that exists is the convention.** Before writing anything:

1. Find the closest case in `backend/src` and **copy it**: structure, names, comments, the shape of the queries, the tests.
2. If this file and the code disagree, the code wins. Tell the owner, so this file gets fixed.
3. If there is no similar case, **ask before writing it**. No new pattern on your own: Protocols, factories, generic helpers, base classes, another way of writing queries...
4. Committed code isn't retouched for style. It only changes when something new needs it (an import, a comment that is no longer true).

## How we work

- The owner decides. Propose, explain and wait for the OK on anything that wasn't asked for. An ambiguous phrase is not permission.
- **Never commit or push** unless the owner says so in those words ("make the commit", "push"). Say first what goes in each commit. A "yes" to another question is not permission to commit.
- One commit per change, conventional commits in English, **without** `Co-Authored-By` or any attribution to an AI.
- Every commit has a **broad title** that names the piece (`feat(auth): add password login`, `feat(user): add the users table`), not a long sentence describing the behavior, and under it a **very visual description**: one-word sections with dashes below, saying what the commit does without explaining the code. The sections are `API`, `DB`, `Flow`, `Security`, `Limits`, `Mail`, `Logs`, `Settings`, `Repository`, `Schemas`, `Fix`, `Refactor`, `Why`, `Deps`, `Repo`, `CI`, `Frontend` and `Tests`, only the ones that are needed. Lines of 72 characters at most:
  ```
  feat(auth): add password login

  API
  - POST /auth/login -> session cookie

  Limits
  - 60/minute and 2000/day per IP

  Tests
  - test_login.py
  ```
- A commit carries only what its message says, and its comments don't name code that doesn't exist yet in that commit.
- If the owner asks to put a fix in the history, it goes in the commit where it should have been: rewrite in a separate clone, check that authors, dates and messages don't change, and force push with `--force-with-lease` only if it was asked for.
- **Don't** install dependencies, bump versions, change the database schema or reopen closed decisions without talking about it first. Don't invent features.
- No `.env` file in the repository, not even examples.
- Nothing on the machine is touched or inspected outside the code, the tests, the docs, the IDE and Docker for the tests.
- After every change, with `db` and `redis` up: `docker compose run --rm -T --no-deps backend sh -c 'ruff check . && pyright && pytest -q'`.
- When the tests end, stop the containers: `docker compose stop`.
- At most 2 test containers at once and short runs. Anything heavy (mutants, checking commit by commit) goes in chunks of about 10 minutes, and if something drags on, stop and tell the owner.

## Backend structure

```
src/main.py                    app, logging middleware, CORS, routers (registered after setup_openapi)
src/api/dependencies.py        dependencies and their Annotated type (Language...)
src/api/routers/<area>_router.py
src/modules/<module>/          module in singular (demo)
    models/<thing>_model.py
    repositories/<thing>_repository.py
    schemas/<thing>_schemas.py
    services/<thing>_service.py
    translations/<thing>_translations.json
src/core/                      settings, errors, languages, logger, limiter, request_context
src/mail/sender.py             send_email (in the background)
src/mail/templates/<name>.py
src/mail/translations/<name>_translations.json
src/database/                  Base, session (get_db, DbSession), models.py (imports every model)
src/shared/schemas.py          MessageResponse {message}, ErrorResponse {detail}
```

A request goes router → service → repository. Files in `snake_case`, one per concept.

A folder with files has no `.gitkeep`: it goes in the commit that adds the first file.

## Routers

Example: `api/routers/demo_router.py`.

- `router = APIRouter(prefix="/email-requests", tags=["Email requests"])`.
- Every route has its limits per IP, by minute and by day, chosen by how often the action repeats: `5/minute;50/day` for what sends an email, `60/minute;2000/day` for a read. The limit is written in the decorator and has a row in `tests/test_limiter.py`.
- The file has **only** endpoint functions. Each one has a single line that returns what the service returns: `return await email_request_service.create_email_request(db, body, language, background_tasks)`.
- The endpoint has the same name as the service function it calls.
- First `@router.post("", status_code=status.HTTP_201_CREATED)` and below it `@limiter.limit("5/minute;50/day")`.
- Parameters in the order `request, body, db, language, background_tasks`, with their types (`db: DbSession`, `language: Language`).
- Above each endpoint, a comment with what isn't obvious (why that limit...).
- A new router is registered in `main.py` with `app.include_router(...)`, after `setup_openapi(app)`.

## Dependencies

Example: `get_language` + `Language`.

- First the function and, right below it, its type with a usage comment: `# Language of the request, in an endpoint: language: Language` and `Language = Annotated[str, Depends(get_language)]`.
- The ones that only let the request through are used as `dependencies=[Depends(...)]`.

## Services

Example: `modules/demo/services/email_request_service.py`.

- One service per area, not per function. One function per endpoint. It receives `db`, `body`, `language`, `background_tasks` (the ones it needs) and returns a Pydantic schema (`MessageResponse`).
- Comments: above the function, what it does and why, with a list of dashes if there are several guarantees; inside, only the steps that aren't obvious, in a short sentence.
- The flow reads top to bottom. Steps that aren't obvious get a comment above (`# Built before saving: ...`). Steps are only numbered (`# 1. ...`) when the logic is really tedious, as in `get_language`.
- **One `await db.commit()`, at the end of the flow**, and what gets logged is written after it.
- Two similar flows have **their own service each**, even if code repeats. No generic service with the variant as a parameter.
- When an `if/elif/else` splits business cases, **each branch does all of its work** (no `else` that only logs because the work is after the `if`) and **each case has its comment**: what happens and why.
- Each query goes in the step that uses it, not at the beginning: if an earlier step fails, it wasn't run for nothing.
- If a new path creates something that only another flow created before, check what that flow assumed.
- Service constants go on top, with a comment.
- Errors are raised where they happen, with `raise HTTPException(status_code=status.HTTP_..., detail=get_error_detail(NAME, language))`. **Only** if the same exception is raised in **several places**, a private helper **returns** it and the caller **raises** it (`_already_requested`). A helper for an error used once inflates the code for nothing.
- Responses: `MessageResponse(**get_response("EMAIL_REQUEST_CREATED", language))`. When the same text is returned in several places, take it out first in a variable and use `MessageResponse(message=message)`.
- Emails are built **before** saving anything (`build_x_email(language, ...)`) and sent after the response with `background_tasks.add_task(send_email, subject, [email], html)`. `DbSession` closes when the endpoint ends (`scope="function"`): a background task holds no connection and can't use `db`.
- Only foreseeable errors are caught. The rest becomes a translated 500.
- A constraint error (`IntegrityError`) is caught in the service and answered with a translated error: if it reaches the traceback, the `DETAIL` of PostgreSQL shows the value (`Key (email)=(...) already exists`) and puts personal data in the logs (see `database/session.py`).
- A `raise` inside an `except` always has `from` (ruff B904), chosen by what is raised:
  - **A response** (`HTTPException`): `from None`. It says "the previous one is solved, this is the answer", like `raise _already_requested(language) from None`.
  - **Another error**: `from exc`. It says "this happens because of that" and keeps the original: if the new error ends in a 500, its traceback shows what really failed.

## Repositories

Example: `modules/demo/repositories/email_request_repository.py`.

- Every file starts, after the imports, with `# No commit and no rollback here: the service commits once, at the end of its flow.` and `# On any error the request ends and closing the session (get_db) rolls it back`.
- Only database queries: no `try/except` and no business logic.
- **A repository never commits.** `tests/test_repositories.py` checks it. A dependency that writes also commits itself, at its end.
- Two functions that do the same are unified with a parameter. If they stay separate for a reason, the name says which one is which.
- `flush()` only when the id is needed in the same flow, or so a constraint fires where it is caught (`create_email_request`).
- Names, one verb per kind of action:

  | Prefix | What it does | Example |
  |---|---|---|
  | `get_<thing>_by_<key>` | Finds a row or `None` | `get_email_request_by_email` |
  | `get_<things>` | Lists rows | `get_email_requests` |
  | `get_<thing>_with_<other>_by_<key>` | Brings both together | — |
  | `get_valid_<thing>` | Only if it can still be used | — |
  | `is_...` | Returns a boolean | — |
  | `create_<thing>` | Inserts | `create_email_request` |
  | `set_...` / `update_<field>` | Changes a value | — |
  | `mark_<thing>_used` | Only stamps the date of last use | — |
  | `use_<thing>` | Spends something of a single use | — |
  | `revoke_<thing>` / `revoke_<things>` | Singular: one by id. Plural: the pending ones of a group | — |

- Parameters: `db` first, and ids are passed, not objects. The exception is when the object is read afterwards.
- A function returns `None`, unless someone reads what it returns.
- Queries:
  - One object or `None`: `await db.scalar(query)`.
  - By primary key: `await db.get(Model, id)`.
  - Several columns: `row = (await db.execute(query)).first()` and `return (row[0], row[1]) if row else None`.
  - With one condition it fits in a line: `return await db.scalar(select(EmailRequest).where(EmailRequest.email == email))`.
  - With several, it goes in a variable `query = (...)`, each condition on its line.
- Dates the object needs after the commit: `datetime.now(UTC)`. In an `update(...).values(...)`: `func.now()`.
- If two requests at once can step on each other, `.with_for_update()` and a comment explaining it. Two flows that lock the same rows do it in the same order, or they can deadlock.

## Models

Example: `modules/demo/models/email_request_model.py`.

- Class in singular (`EmailRequest`) and table in plural (`email_requests`). Every model is imported in `src/database/models.py`.
- PostgreSQL enums are `enum.StrEnum`, with the comment `# Values of the <name> enum of PostgreSQL`, mapped with `Enum(..., name="...", values_callable=lambda e: [member.value for member in e])`.
- `id`: `mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))`. Dates: `DateTime(timezone=True)`, with `server_default=func.now()` when the database sets them.
- Every column and every constraint of `__table_args__` that isn't obvious has its comment above.
- A value that may be unknown is **nullable** and saved as `NULL`, never `""` or a made-up value. If a form requires it, its schema requires it, not the column.
- A column the app always fills is `NOT NULL`.
- A nullable `JSONB` column uses `JSONB(none_as_null=True)`: otherwise `None` is saved as the JSON `null`, not as `NULL`.
- A column queried on every request gets an index (`index=True`, with a comment saying why): PostgreSQL doesn't index foreign keys by itself.
- Migrations with `alembic revision --autogenerate`. They are reviewed and tried against an `app_check` database: `upgrade`, `alembic check`, `downgrade`, `upgrade`. Then it is deleted.
- Migrations must work **with data**: the one that sets a `NOT NULL`, in `upgrade` or in `downgrade`, fills the `NULL`s first. Try it with a row that needs it.
- When finished, apply it to the development database: `docker compose run --rm -T --no-deps backend alembic upgrade head`.

## Schemas

Example: `modules/demo/schemas/email_request_schemas.py`.

- Request bodies with the comment `# Body of POST /...`.
- A schema that can serve more cases is named after what it carries, not after its endpoint: `EmailSchema`, which only receives an email.
- Limits as constants, and reusable types with `Annotated`.
- Emails are lowercased with a `field_validator("email")` called `lowercase_email`.
- A value the app generates (the token of a link) is validated with its exact shape: `Field(pattern=r"^[A-Za-z0-9_-]{43}$")`. What has no fixed shape, with a maximum.
- Responses from outside declare only the fields that are used: a required field nobody reads would break the flow if the provider stops sending it.
- Free text going to the database rejects the NUL character (`pattern=r"^[^\x00]*$"`): PostgreSQL can't store it and it would be a 500. What comes from an outside provider isn't refused, it is cleaned in its schema: an odd value can't stop the flow.

## Translations

- A `*_translations.json` file with 4 spaces of indentation. Names in uppercase, languages with the main one first, the same keys in all of them:
  ```json
  "EMAIL_REQUEST_CREATED": {
      "en": {
          "message": "..."
      },
      "es": {
          "message": "..."
      }
  }
  ```
- `message` for successes, `detail` for errors. Placeholders are `%s`. In Spanish the user is addressed as "tú".

## Code style

- **Comments** in English, **above** every function, class and constant of `src/`: what it does and, above all, why. No docstrings. If they take several lines, sentences are separated with a period, but **the last line never ends in a period**. In the tests, see their section.
- **Optional values**: always `if value:` / `if not value:`. Never `is None` / `is not None`. Only in SQL: `.is_(None)`.
- **Exact types**: `X | None` only if it can really be missing. If it always arrives, the type doesn't allow it. What isn't known is `None`/`NULL`, never a made-up value; the only exception is `"unknown"` in `get_client_ip`.
- **Status codes**: `status.HTTP_...` of FastAPI, also when comparing them (`response.status_code >= status.HTTP_400_BAD_REQUEST`).
- **Lines** of 120 characters at most. Double quotes and a trailing comma in whatever is split over several lines (ruff COM812). Imports in three groups: standard, third party and `src` (ruff sorts them).
- **Signatures**: on one line if they fit. If not, one parameter per line with a trailing comma. The only exception is `error_response`.
- **Calls**: on one line by default. They are split when they don't fit or read better that way, one argument per line with a trailing comma.
- **Logs** (`logger = logging.getLogger(__name__)`): fixed message, data in `extra={...}` and never personal data, tokens or passwords (emails masked with `_mask_email`). The logger adds the request id and the IP by itself.
  - Something created or changed: `info` with its id as it is, without `str()`, **after** the commit, never before saving: `logger.info("Email request saved", extra={"email_request_id": email_request.id})`.
  - A flow that can end in several ways: a single log at the end with the result in `extra`.
  - An external service that fails: `warning` if the app goes on and the user can retry, `error` if something is lost. The text of the error goes in the message with `%s`, not in `extra`: `logger.error("Could not connect to the mail server: %s", exc, extra={...})`. If that text may carry personal data, only its type: `type(exc).__name__`.
  - Not logged: reads, 4xx errors (the middleware of `main.py` writes them, the service only raises its `HTTPException`) and unexpected 500s of a request (the middleware writes them with `logger.exception` and their traceback).
  - The traceback: `%s` only puts the message of the error in the line; the traceback only comes with `logger.exception(...)` or `exc_info=True`. Use it only for the unexpected outside a request, where the middleware doesn't reach (background tasks, scheduled processes).

## Settings

- All required, without a default, and each one (or each group, like `POSTGRES_*` or `MAIL_*`) with its comment above.
- They are normalized with a `field_validator(..., mode="before")` and the production rules go in `check_combinations`.
- A new variable goes in `settings.py`, in `env` of `.github/workflows/ci.yml`, in `VALID` of `tests/test_settings.py`, in the block of the README quick start and, if the tests need a fixed value, in `tests/conftest.py`.

## Security

- What arrives from the browser (a cookie, a body) is compared with `secrets.compare_digest` **in bytes** (`.encode()`): with non-ASCII text it raises `TypeError` and it would be a 500.
- A secret that goes to the user (a token, a code) is saved only as its hash.
- The real IP behind a proxy is configured when deploying, without code: the proxy's IP goes in `FORWARDED_ALLOW_IPS`, and uvicorn only trusts `X-Forwarded-For` if the request comes from there.

## Tests

Examples: `test_email_requests.py`, `test_errors.py`.

- One file per area: `tests/test_<thing>.py`. The test database is `app_test`, built from the models: what only exists in the migrations (a trigger) is tested on its own database, created with `alembic upgrade head`.
- Fixtures: `client`, which calls the app and empties the tables with `clean_state`. `clean_state` alone, in repository tests.
- External services are never called: they are replaced with `monkeypatch` (the fixture `sent_emails` replaces `send_email` of the service).
- The name of the test says what happens: `test_create_twice_is_a_conflict`.
- Constants go on top and helpers are functions of the file itself (`create`).
- In the tests, comments only when something isn't obvious: what a fixture simulates or why a test does what it does.
- In asserts, status codes are compared with the number (`response.status_code == 200`), and conditions are joined with `and`.

## Before calling something done

- ruff, pyright and pytest clean, and `alembic check` without changes with the development database at `head`.
- Nothing defined and unused: every new function, constant, schema field and translation is used in `src` (`test_every_translation_is_used` checks the translations), and a repository doesn't return what nobody reads.
- The critical lines have a test that pins them: if one is broken on purpose (removing a filter by user, a limit, an `await`), some test has to fail. What filters by user is tested with two users.
- What a comment or this file promises is also broken on purpose: that a limit exists on every route, that the storage doesn't keep an email. A test that only checks that a value exists doesn't pin it: compare it with its value.
- A limit per hour or per day can't be waited for in a test: it is pinned by comparing it (`tests/test_limiter.py`). `caplog.text` doesn't include `extra`: a `not in` on it proves nothing.
- Two twin flows are compared by replacing the name of each one with a common one: only their own lines can differ. **Their tests too**.
- What goes to production and doesn't run in the tests is also tried, in a new process with the production settings.
- What can be tried against the real server, is tried.
- To check old commits: in a separate clone, mounted with `docker compose run -v <clone>/backend:/app`, and with `app_test` dropped first, because the tables of the current version give false errors on `drop_all`.
- The README says what the code does, and the other way around.

## Frontend

The conventions are in the README (*Frontend guide* and *Conventions*): every page and component is a folder with its JSX, CSS module, translations and tests, colors come from the variables of `themes.css`, and every text is translated. The checks are `docker compose run --rm -T --no-deps frontend sh -c 'npx oxlint src && npm test && npm run build'`.
