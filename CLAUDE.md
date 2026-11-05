# FastAPI-React-Template

Full-stack base to clone and build on: FastAPI (async SQLAlchemy, Alembic, PostgreSQL, Redis rate limiting, email) and React + Vite, all in Docker. The only feature is a demo, `modules/demo/`: it is the reference for every new module, and it is removed when a real project starts (see the README, *Starting a project*).

This file says how to work on the template and on anything built from it. The README has the setup and the guides for people.

<!-- A project built from the template changes the title and the paragraph above to its own, and writes here, under
     "## This project", what is its own: its modules, its decisions and where its documentation lives. The rest of the
     file is the way of working, kept as it is -->

## Rule number one: don't invent style

**The code that exists is the convention.** Before writing anything:

1. Find the closest case in the code and **copy it**: structure, names, comments, the shape of the queries, the tests. Most `Example:` lines name files of the demo; in a project built from the template the demo is gone, and it is read in the template's repository: https://github.com/davidcastillocruz/FastAPI-React-Template (`gh api repos/davidcastillocruz/FastAPI-React-Template/contents/<path>`).
2. If this file and the code disagree, the code wins. Tell the owner, so this file gets fixed.
3. If there is no similar case, **ask before writing it**. No new pattern on your own: Protocols, factories, generic helpers, base classes, another way of writing queries...
4. Committed code isn't retouched for style. It only changes when something new needs it (an import, a comment that is no longer true) or the owner asks for it.

## How we work

- The owner decides. Propose, explain and wait for the OK on anything that wasn't asked for. An ambiguous phrase is not permission.
- **Don't** install dependencies, bump versions, change the database schema or reopen closed decisions without talking about it first. Don't invent features.
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
  - test_login.py, test_limiter.py
  ```
- A commit carries only what its message says, and its comments don't name code that doesn't exist yet in that commit.
- If the owner asks to put a fix in the history, it goes in the commit where it should have been: rewrite in a separate clone, check that authors, dates and messages don't change, and force push with `--force-with-lease` only if it was asked for.
- No `.env` file in the repository, not even examples.
- Nothing on the machine is touched or inspected outside the code, the tests, the docs, the IDE and Docker.
- After every change, with `db` and `redis` up: `docker compose run --rm -T --no-deps backend sh -c 'ruff check . && pyright && pytest -q'`, and for the frontend `docker compose run --rm -T --no-deps frontend sh -c 'npx oxlint src && npm test && npm run build'`.
- When the tests end, stop the containers: `docker compose stop`. Docker itself stays open.
- At most 2 test containers at once and short runs. Anything heavy (mutants, checking commit by commit) goes in chunks of about 10 minutes, and if something drags on, stop and tell the owner.

## Backend

```
src/main.py                    app, middlewares (body size, logs, CORS), routers (registered after setup_openapi)
src/api/dependencies.py        dependencies and their Annotated type (Language...)
src/api/routers/<area>_router.py
src/modules/<module>/          module in singular (demo): models/, repositories/, schemas/, services/, translations/,
                               and a folder for each other job of the module (talking to a provider, handling files...)
src/core/                      settings, errors, languages, logger, limiter, request_context
src/mail/                      sender.py (send_email), layout.py (the HTML of every email), emails.py (each email),
                               translations/ (one JSON per email)
src/database/                  Base, session (get_db, DbSession), models.py (imports every model)
src/shared/schemas.py          MessageResponse {message}, ErrorResponse {detail}
```

A request goes router → service → repository. Files in `snake_case`, one per concept. A folder with files has no `.gitkeep`: it goes in the commit that adds the first file.

### Routers

Example: `api/routers/demo_router.py`.

- `router = APIRouter(prefix="/email-requests", tags=["Email requests"])`, registered in `main.py` with `app.include_router(...)`, after `setup_openapi(app)`.
- The file has **only** endpoint functions. Each one has a single line that returns what the service returns, and the same name as the service function it calls: `return await email_request_service.create_email_request(db, body, language, background_tasks)`. A response that isn't a schema (a file, a redirect) is also built by the service.
- First `@router.post("", status_code=status.HTTP_201_CREATED)` and below it `@limiter.limit(EMAIL_LIMIT)`.
- Parameters in the order `request, body, db, language, background_tasks`, with their types (`db: DbSession`, `language: Language`).
- Above each endpoint, a comment with what it does and what isn't obvious about it, one line when that's all, never why its limit is what it is: its constant says that.
- **Limits**: every route has one of the constants of `core/limiter.py`, explained there once and chosen by how often a person repeats the action (`READ_LIMIT`, `EMAIL_LIMIT`). Never a number in a decorator: a new kind of action adds its constant. Each route has its row in `tests/test_limiter.py`. What has to be stricter (the failures of a password, the emails to one address) has its own limit inside its service.
- A route with a session counts per user, not per IP (`key_func=` a dependency that reads the user): per IP, one person in a loop would leave everyone behind the same IP (a school, an office) without it.
- No body goes over `MAX_BODY_BYTES` (`limit_body_size` in `main.py`): FastAPI reads a whole body before the endpoint runs. A route that takes files raises it to what it needs, after talking about it.

### Dependencies

Example: `get_language` + `Language`.

- First the function and, right below it, its type with a usage comment: `# Language of the request, in an endpoint: language: Language` and `Language = Annotated[str, Depends(get_language)]`.
- The ones that only let the request through are used as `dependencies=[Depends(...)]`.

### Services

Example: `modules/demo/services/email_request_service.py`.

- One service per area, not per function. One function per endpoint. It receives `db`, `body`, `language`, `background_tasks` (the ones it needs) and returns a Pydantic schema (`MessageResponse`).
- A private function of the flow itself can live in the service, but another job (talking to a provider, converting an image, handling files) goes in its own folder of the module, not as loose functions of the service.
- Comments: above the function, what it does and why, with a list of dashes if there are several guarantees; inside, only the steps that aren't obvious, in a short sentence. Steps are only numbered (`# 1. ...`) when the logic is really tedious, as in `get_language`.
- **One `await db.commit()`, at the end of the flow**, and what gets logged is written after it.
- Two similar flows have **their own service each**, even if code repeats. No generic service with the variant as a parameter.
- When an `if/elif/else` splits business cases, **each branch does all of its work** (no `else` that only logs because the work is after the `if`) and **each case has its comment**: what happens and why.
- Each query goes in the step that uses it, not at the beginning: if an earlier step fails, it wasn't run for nothing.
- If a new path creates something that only another flow created before, check what that flow assumed.
- Service constants go on top, with a comment.
- Errors are raised where they happen, with `raise HTTPException(status_code=status.HTTP_..., detail=get_error_detail(NAME, language))`. **Only** if the same exception is raised in **several places**, a private helper **returns** it and the caller **raises** it (`_already_requested`). A helper for an error used once inflates the code for nothing.
- Responses: `MessageResponse(**get_response("EMAIL_REQUEST_CREATED", language))`. When the same text is returned in several places, take it out first in a variable and use `MessageResponse(message=message)`.
- **Emails** are built **before** saving anything (`build_x_email(language, ...)`) and sent after the response with `background_tasks.add_task(send_email, subject, [email], html)`. Each email is a function of `mail/emails.py`: its texts (`mail/translations/`, one JSON per email), what fills their gaps and what it shows under the text. The HTML, with inline styles, is the same for all of them (`render_email` in `mail/layout.py`, which escapes everything). An email with another shape adds an option to `render_email`, never a copy of the HTML. `DbSession` closes when the endpoint ends (`scope="function"`): a background task holds no connection and can't use `db`.
- What takes long in the CPU (image processing, password hashing) goes in `asyncio.to_thread`.
- Only foreseeable errors are caught. The rest becomes a translated 500.
- A constraint error (`IntegrityError`) is caught in the service and answered with a translated error: if it reaches the traceback, the `DETAIL` of PostgreSQL shows the value (`Key (email)=(...) already exists`) and puts personal data in the logs (see `database/session.py`).
- A `raise` inside an `except` always has `from` (ruff B904), chosen by what is raised:
  - **A response** (`HTTPException`): `from None`. It says "the previous one is solved, this is the answer", like `raise _already_requested(language) from None`.
  - **Another error**: `from exc`. It says "this happens because of that" and keeps the original: if the new error ends in a 500, its traceback shows what really failed.
- A task that runs on its own while the app does (deleting what expired) starts in the `lifespan` of `main.py` with `asyncio.create_task` and is cancelled on shutdown. It opens its own session, commits each item on its own, and logs its failures with `logger.exception`.

### Repositories

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
- **Locks**: if two requests at once can step on each other, `.with_for_update()` and a comment explaining it.
  - If the flow only changes columns that aren't keys, `with_for_update(key_share=True)` (`FOR NO KEY UPDATE`): a plain `FOR UPDATE` also waits for the `FOR KEY SHARE` that an insert of another request takes on its foreign key, and the two block each other.
  - A row read again under a lock that the session already holds comes from memory, not from the database: that read uses `populate_existing` (`execution_options(populate_existing=True)`, or `db.get(..., populate_existing=True)`).
  - Two flows that lock the same rows do it in the same order, or they can deadlock. When they can't (a background task against a request), the one that can wait yields: `SET LOCAL lock_timeout` short, and it tries again later.

### Models and migrations

Example: `modules/demo/models/email_request_model.py`.

- Class in singular (`EmailRequest`) and table in plural (`email_requests`). Every model is imported in `src/database/models.py`.
- PostgreSQL enums are `enum.StrEnum`, with the comment `# Values of the <name> enum of PostgreSQL`, mapped with `Enum(..., name="...", values_callable=lambda e: [member.value for member in e])`. A new value is added in the migration by hand (`ALTER TYPE ... ADD VALUE`), and its `downgrade` recreates the type.
- `id`: `mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))`. Dates: `DateTime(timezone=True)`, with `server_default=func.now()` when the database sets them.
- Every column and every constraint of `__table_args__` that isn't obvious has its comment above.
- A value that may be unknown is **nullable** and saved as `NULL`, never `""` or a made-up value. If a form requires it, its schema requires it, not the column. A column the app always fills is `NOT NULL`.
- A nullable `JSONB` column uses `JSONB(none_as_null=True)`: otherwise `None` is saved as the JSON `null`, not as `NULL`.
- A column queried on every request gets an index (`index=True`, with a comment saying why): PostgreSQL doesn't index foreign keys by itself. A column that is only searched when it has a value gets a partial index (`postgresql_where`).
- Migrations with `alembic revision --autogenerate`. They are reviewed and tried against an `app_check` database: `upgrade`, `alembic check`, `downgrade`, `upgrade`. Then it is deleted.
- Migrations must work **with data**: the one that sets a `NOT NULL`, in `upgrade` or in `downgrade`, fills the `NULL`s first. Try it with a row that needs it.
- When finished, apply it to the development database: `docker compose run --rm -T --no-deps backend alembic upgrade head`.

### Schemas

Example: `modules/demo/schemas/email_request_schemas.py`.

- Request bodies with a comment saying what they carry: `# Body of POST /...`, or for one that serves more cases `# Body with only an email, like POST /email-requests`.
- A schema that can serve more cases is named after what it carries, not after its endpoint: `EmailSchema`, which only receives an email.
- Limits as constants, and reusable types with `Annotated`.
- Emails are lowercased with a `field_validator("email")` called `lowercase_email`.
- A value the app generates (the token of a link) is validated with its exact shape: `Field(pattern=r"^[A-Za-z0-9_-]{43}$")`. What has no fixed shape, with a maximum.
- Responses from outside declare only the fields that are used, and of a list only the item that is used: a required field nobody reads would break the flow if the provider stops sending it.
- Free text going to the database rejects the NUL character (`pattern=r"^[^\x00]*$"`): PostgreSQL can't store it and it would be a 500. What comes from an outside provider isn't refused, it is cleaned in its schema: an odd value can't stop the flow.

### Translations

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
- `message` for successes, `detail` for errors. Emails use the keys `render_email` reads (`subject`, `title`, `text`, `footer`...). Placeholders are `%s`. In Spanish the user is addressed as "tú".

### Code style

- **Comments** in English, **above** every function (also the ones inside another), class and constant (in uppercase) of `src/`: what it does and, above all, why. No docstrings. If they take several lines, sentences are separated with a period, but **the last line never ends in a period**. In the tests, see their section.
- **Optional values**: in a condition (an `if`, a ternary, the filter of a comprehension) always `if value:` / `if not value:`, never `is None` / `is not None`. Only in SQL: `.is_(None)`. The `assert` of a test can check `is None`: it says the value is exactly `None`. If "it didn't arrive" and a falsy value mean different things, change the shape: an optional boolean with `isinstance(value, bool)`, a test helper with a separate parameter (`with_cookie=False` against `cookie=""`).
- **Exact types**: `X | None` only if it can really be missing. If it always arrives, the type doesn't allow it. What isn't known is `None`/`NULL`, never a made-up value; the only exception is `"unknown"` in `get_client_ip`.
- **Status codes**: `status.HTTP_...` of FastAPI, also when comparing them (`response.status_code >= status.HTTP_400_BAD_REQUEST`).
- **Lines** of 120 characters at most. Double quotes and a trailing comma in whatever is split over several lines (ruff COM812). Imports in three groups: standard, third party and `src` (ruff sorts them).
- **Signatures and calls**: on one line if they fit; a call is also split when it reads better that way. Split, one item per line with a trailing comma. The only exception is `error_response`. Dictionaries that work as a table (one entry per case, like `ROUTING_ERRORS`), one entry per line.
- **Logs** (`logger = logging.getLogger(__name__)`): fixed message, data in `extra={...}` and never personal data, tokens or passwords (emails masked with `_mask_email`). The logger adds the request id and the IP by itself.
  - Something created or changed: `info` with its id as it is, without `str()`, **after** the commit, never before saving: `logger.info("Email request saved", extra={"email_request_id": email_request.id})`.
  - A flow that can end in several ways: a single log at the end with the result in `extra`.
  - An external service that fails: `warning` if the app goes on and the user can retry, `error` if something is lost. The text of the error goes in the message with `%s`, not in `extra`: `logger.error("Could not connect to the mail server: %s", exc, extra={...})`. If that text may carry personal data, only its type: `type(exc).__name__`.
  - Not logged: reads, 4xx errors (the middleware of `main.py` writes them, the service only raises its `HTTPException`) and unexpected 500s of a request (the middleware writes them with `logger.exception` and their traceback).
  - The traceback: `%s` only puts the message of the error in the line; the traceback only comes with `logger.exception(...)` or `exc_info=True`. Use it only for the unexpected outside a request, where the middleware doesn't reach (background tasks, scheduled processes).

### Settings

- All required, without a default, and each one (or each group, like `POSTGRES_*` or `MAIL_*`) with its comment above.
- They are normalized with a `field_validator(..., mode="before")` and the production rules go in `check_combinations`.
- A new variable goes in `settings.py`, in `env` of `.github/workflows/ci.yml`, in `VALID` of `tests/test_settings.py`, in the block of the README quick start and, if the tests need a fixed value, in `tests/conftest.py`.

### Security

- What arrives from the browser (a cookie, a body) is compared with `secrets.compare_digest` **in bytes** (`.encode()`): with non-ASCII text it raises `TypeError` and it would be a 500.
- A secret that goes to the user (a token, a code) is saved only as its hash.
- Cookies are set and deleted only through helpers of their own, with the same options everywhere.
- The real IP behind a proxy is configured when deploying, without code: the proxy's IP goes in `FORWARDED_ALLOW_IPS`, and uvicorn only trusts `X-Forwarded-For` if the request comes from there.

### Tests

Examples: `test_email_requests.py`, `test_errors.py`.

- One file per area: `tests/test_<thing>.py`. The test database is `app_test`, built from the models: what only exists in the migrations (a trigger) is tested on its own database, created with `alembic upgrade head`.
- Fixtures: `client`, which calls the app and empties the tables with `clean_state`. `clean_state` alone, in repository tests.
- External services are never called: they are replaced with `monkeypatch` (the fixture `sent_emails` replaces `send_email` of the service), or their HTTP client with an `httpx.MockTransport`. Files go to `tmp_path`, never to the folders of the app.
- The name of the test says what happens: `test_create_twice_is_a_conflict`.
- Constants go on top and helpers are functions of the file itself (`create`).
- In the tests, comments only when something isn't obvious: what a fixture simulates or why a test does what it does.
- In asserts, status codes are compared with the number (`response.status_code == 200`), and conditions are joined with `and`.
- Never `monkeypatch.undo()` in the middle of a test: it undoes the fixtures too.
- Requests at once: `asyncio.gather` of several (with 2 the race doesn't always happen), and the test has to fail without the lock. When the order matters, it is forced: the repository function is replaced by one that waits for an `asyncio.Event`.

### Before calling something done

- ruff, pyright and pytest clean, and `alembic check` without changes with the development database at `head`.
- Nothing defined and unused: every new function, constant, schema field and translation is used in `src` (`test_every_translation_is_used` checks the translations), and a repository doesn't return what nobody reads.
- The critical lines have a test that pins them: if one is broken on purpose (removing a filter by user, a limit, an `await`, a lock), some test has to fail. What filters by user is tested with two users.
- What a comment or this file promises is also broken on purpose: that a limit exists on every route, that the storage doesn't keep an email. A test that only checks that a value exists doesn't pin it: compare it with its value.
- A limit per hour or per day can't be waited for in a test: it is pinned by comparing it (`tests/test_limiter.py`). `caplog.text` doesn't include `extra`: a `not in` on it proves nothing.
- Two twin flows are compared by replacing the name of each one with a common one: only their own lines can differ. **Their tests too**.
- A refactor that shouldn't change what comes out is compared with what came out before (the HTML of every email, byte by byte).
- What goes to production and doesn't run in the tests is also tried, in a new process with the production settings.
- What can be tried against the real server, is tried.
- To check old commits: in a separate clone, mounted with `docker compose run -v <clone>/backend:/app`, and with `app_test` dropped first, because the tables of the current version give false errors on `drop_all`.
- The README says what the code does, and the other way around.

## Frontend

React 19 with Vite, React Router, axios and CSS Modules, in JavaScript.

```
src/main.jsx                   providers (Theme > Language) and every route
src/index.css                  global styles
src/themes/  src/languages/    theme and language systems (provider, context, hook)
src/utils/                     api.js (axios), cookies.js
src/components/<Name>/         <Name>.jsx, <Name>Style.module.css, <Name>Translation.json, <Name>.test.jsx
src/pages/<Name>Page/          pages on their own (HomePage, NotFoundPage), same files
src/hooks/                     hooks shared by several features
src/features/<area>/           a big feature: its components/, pages/ and hooks/
src/test/                      setup of the tests
```

- **Imports**: three groups (packages, `@/`, `./`), each in alphabetical order of the path, and the stylesheets last in their group (`themes.css` before `index.css` in `main.jsx`). Never `../`.
- **Components**: one exported per file, `export default`, with a comment saying what it is and the props that don't explain themselves. A small piece that only it uses can go in the same file, with its comment (`FlapCell` in `SplitFlap.jsx`). Props with their default in the signature.
- **Contexts**: `<Name>Context.js` only with `createContext`, the provider apart, read with `use()`; if several components read it, with a hook of its own (`useTheme`, `useLanguage`).
- **Styles**: the colors are the variables of `themes.css`, and a new one goes in both themes; a loose color only if it is the same in both. The font and the easings are the variables of `index.css`. Rules that aren't obvious are commented. `:hover` inside `@media (hover: hover) and (pointer: fine)`. The states the CSS paints, as `data-` attributes, or the `aria-` one that already says it (`aria-pressed`, `aria-disabled`). `clamp()` for fluid sizes, `px` for the rest of the text.
- **Responsive**: everything is usable at 375 px without horizontal scroll. The cuts go where the content asks for them, in the CSS of each component (the home page changes at 520 and 880 px). What doesn't shrink scrolls inside its container.
- **Texts**: never in the JSX. Their `*Translation.json` (2 spaces, the main language first) and `const t = useT(translations)`; placeholders `{name}`. Numbers and dates with the language. A text that comes from the backend is already translated: it is shown as it comes.
- **Frontend settings**: `VITE_` variables (today `VITE_API_URL`), required and without a default, like the ones of the backend. They go in the `environment` of the `frontend` service of `docker-compose.yml` and in the `env` of the frontend job of `ci.yml`, never in a `.env`, and `vite.config.js` checks them (`checkSettings`): if one is missing or wrong, the server, the build and the tests don't start.
- **Requests**: always with `api` (`utils/api.js`). A form shows the `detail` of the backend, or its own text when there is none (no answer, a proxy's page). What the response of a change already says is not asked again.
- **Routes**: every page in `main.jsx`, and the `*` route stays last with `NotFoundPage`.
- **Accessibility**: decorative things with `aria-hidden`, images that mean something with a translated description, everything usable with the keyboard, and the focus is never lost. A disabled button loses the focus: a control used while it saves stays enabled and ignores what arrives, and if one disappears when it ends, the focus goes to what replaces it.
- **Animations**: CSS if the path is fixed, `element.animate` if it depends on measuring. Always with "reduce motion" (the final state at once) and cancelled when the component unmounts. Reused times, in constants.
- **Effects**: what they open they close in their `return`. One that asks for something again clears the previous error when it works, and what is already loaded isn't asked for again when the language changes.
- **Modal windows**: `<dialog>` with `showModal()` and `close()` in a `useLayoutEffect` (in a `useEffect` the browser doesn't give the focus back). While it saves, neither Cancel nor Escape closes it.
- **Gestures**: what is measured from the event is computed in the event, never inside the function of a `setState`.
- Constants on top, in uppercase and commented: no loose numbers. Module state only if it has to survive the unmount, commented. What two files share, in a file of its own. No `console.log`, commented-out code or anything unused (components, classes, keys).
- **Comments**: like the backend ones, short and plain sentences, three lines at most (six in a component with several props). A component's says what it is; a constant's, what value it is and where it comes from; inside the code, only what doesn't explain itself. In the CSS, only to explain a decision.
- **Tests**: Vitest and Testing Library next to the component, finding things by role and name; `api` with `vi.mock('@/utils/api', ...)`. What jsdom doesn't have (`element.animate`, `IntersectionObserver`, the `<dialog>`, `URL.createObjectURL`, the canvas...) is set by each test and removed in its `afterEach`, after `cleanup()`. `test/setup.js` leaves every test with a light system, motion, no cookies and nothing rendered. jsdom keeps the focus on a disabled button: the test takes it away, as Chrome does. The name of the test says what happens, and the one of a fix fails with the code from before.

## Reviews

They look for failures and broken rules, not another way of writing the same thing. If something always comes up, a rule is missing or it's an opinion.

- What changed since the last clean review is reviewed; everything only if the owner asks for it.
- Only two things count: a **failure** (a concrete case that gives a wrong result, an error, a leak, or something unusable with the keyboard or on a phone) and a **broken rule** (it contradicts this file, quoting the rule; false comments and unused code included). The rest is a **suggestion**: apart, in one line, and not touched without an OK. An accepted one becomes a rule.
- Every finding is proven first (a failing test, a command, the browser). What isn't reproduced is marked "possible" and isn't fixed.
- It is fixed with the smallest change and a test that failed before, and then only those lines are reviewed again. It ends when the checks pass and no failure or broken rule is left.
- Report: a table with `file:line`, type, what happens and the proof; below it, the suggestions and what wasn't fixed, with its reason.
- What the owner discards or lets pass is written down below and doesn't come back.

### Discarded in reviews

- Rewriting committed comments to new rules: only when the code next to them changes.
