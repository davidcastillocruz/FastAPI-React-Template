# Starting a project

How to turn the template into a new project, clean and with nothing of the demo left, and how to build its first feature the way the template is written. Read it top to bottom once; afterwards [`CLAUDE.md`](CLAUDE.md) holds the rules and the [README](README.md) the guides.

**The idea:** the template is a working app with one feature, the demo. You keep the plumbing (settings, errors, languages, themes, logs, limits, emails, tests, CI), take the demo out, and the demo's code stays in the template's history as the model to copy from.

## 1. Create the repository

1. On GitHub, **Use this template → Create a new repository**: the new one starts with a single commit, without the template's history. Or clone it and start a new history:
   ```bash
   git clone https://github.com/davidcastillocruz/FastAPI-React-Template.git my-project
   cd my-project
   rm -rf .git && git init && git add -A
   git commit -F - <<'EOF'
   chore(repo): start from FastAPI-React-Template

   Repo
   - The template as it is, the demo included
   EOF
   ```
2. Create `backend/.env.api` and `backend/.env.db` with the block of the README's [quick start](README.md#quick-start). They are ignored by git and are never committed, not even as examples.
3. Run it once as it is (`docker compose up --build`) and open http://localhost:5173: if the demo works, the machine is ready. Then `docker compose down -v`, which deletes its database.

## 2. Take the demo out

### Backend

Delete:

- `src/modules/demo/` and `src/api/routers/demo_router.py`
- `src/mail/translations/demo_email_translations.json`
- `alembic/versions/2026_10_23_1946-535dc1133489_create_email_requests.py`, and put a `.gitkeep` in `alembic/versions/` until the first migration: Alembic needs the folder
- `tests/test_email_requests.py`

Edit:

- `src/main.py`: the import and the `include_router` of `demo_router`
- `src/database/models.py`: the import of `EmailRequest`
- `src/mail/emails.py`: `build_demo_email` and its imports. The comment on top stays: the first email of the app goes there
- `src/mail/layout.py`: it has the look of the demo. Keep `render_email` and what it does (escape everything, inline styles, tables), and change the colors, the font and the header for yours. The `board` option is the demo's departures board: remove it with `_flaps`, `_route`, `STATIONS` and the colors only the board uses (`SIGNAL`, `BOARD`, `BOARD_CELL`, `BOARD_TEXT`)
- `src/core/limiter.py`: keep the limit constants your routes use. `EMAIL_LIMIT` is the one of the demo; it stays if your app sends emails from a route
- `tests/conftest.py`: the import of `email_request_service` and the `sent_emails` fixture (it comes back, pointing to your service, when one sends emails)
- `tests/test_email.py`: the tests and imports of `build_demo_email`, and the `flaps` helper with its `import re`. The tests of `send_email` and `_mask_email` stay
- `tests/test_limiter.py`: the rows of `demo_router`, replaced by your routes
- `tests/test_database.py`: `test_database_errors_hide_the_parameters` inserts into `email_requests`; point it to a table of yours with a unique column

Until the app has its first table, repository and route, three tests fail: that one, `test_no_repository_commits` and `test_no_route_goes_without_a_limit`. The last two refuse to pass with nothing to check. All of them turn green with the first module.

### Frontend

- Delete `src/components/SplitFlap/`, and write your own `HomePage` and `NotFoundPage` (same folders and files, see [section 5](#5-the-frontend))
- `src/utils/api.js`: the example paths in its comment
- The look of the demo: `@fontsource-variable/archivo` in `package.json` and `index.css`, and the colors of `src/themes/themes.css`. Replace them with your design (see [section 4](#4-the-design))

## 3. Name the project

| What | Where |
| --- | --- |
| Title and description of the API | `APP_TITLE`, `APP_DESCRIPTION` in `backend/.env.api` and in `env` of `.github/workflows/ci.yml` |
| Name of the frontend package | `name` in `frontend/package.json` |
| Title, description and `lang` of the page | `frontend/index.html` |
| Icon | `frontend/public/favicon.svg` |
| Emails of CI | `MAIL_USERNAME`, `MAIL_FROM` in `ci.yml` |
| README, GIF and license | `README.md`: its top (title, badges, overview with the GIF) presents the template, rewrite it for your project. Keep the quick start and the guides: `CLAUDE.md` and this file point to them. `docs/demo.gif` (delete it). `LICENSE`: your name in the copyright, or another license |

### Languages

The template speaks `en` (main) and `es`. To change them, change all of these together, with the main language first everywhere:

- `MAIN_LANGUAGE` and `AVAILABLE_LANGUAGES` in `backend/.env.api`, `ci.yml` and `tests/conftest.py`
- `LANGUAGES` and `MAIN_LANGUAGE` in `frontend/src/languages/languages.js`, and the comment of `useLanguage.js`
- Every `*_translations.json` of the backend (`src/core/translations/errors_translations.json` and the ones you add) and every `*Translation.json` of the frontend: one entry per language. The backend doesn't start while one misses a language
- The tests that expect those texts and languages: `tests/test_errors.py` and `tests/test_languages.py`

## 4. The design

The frontend has no component library on purpose: the look is yours.

1. **Tokens first.** Write your colors as variables in `src/themes/themes.css`, every variable in both themes (light and dark). Components only use these variables: a loose color is allowed only if it is the same in both themes.
2. **Type.** Install the font with `@fontsource-variable/<font>` (talk about it first: it is a dependency), import it in `index.css` and set `--font`.
3. **The emails** use the same colors and font, written in `backend/src/mail/layout.py` (email clients don't read CSS variables).
4. If the project has a style guide (a document, a Figma file), say where it is in `CLAUDE.md`, and write the rule: what isn't in the guide isn't invented.

## 5. The frontend

```
src/
├── main.jsx                 providers and every route
├── index.css                global styles (font, base elements)
├── themes/  languages/      already done: useTheme(), useLanguage(), useT()
├── utils/api.js             axios with the backend's address (VITE_API_URL) and the cookies
├── components/<Name>/       pieces used by several pages (a Button, a Field)
├── pages/<Name>Page/        pages on their own (HomePage, NotFoundPage)
├── hooks/                   hooks used by several features
└── features/<area>/         a big feature (auth, settings): its own components/, pages/ and hooks/
```

Every component and page is a folder:

```
components/Button/
├── Button.jsx                 export default, a comment saying what it is
├── ButtonStyle.module.css     only variables of themes.css
├── ButtonTranslation.json     its texts, every language (only if it has text)
└── Button.test.jsx            Vitest + Testing Library, by role and name
```

How a page is built:

1. The folder, in `pages/` or in `features/<area>/pages/`.
2. Its texts in its `Translation.json`, read with `const t = useT(translations)`. No text is written in the JSX.
3. Its route in `src/main.jsx`, before the `*` route.
4. Its calls with `api` from `@/utils/api`: on an error, show `error.response.data.detail` (the backend's text, already translated) or your own text when there is none (see the README, *Calling the API*).
5. It works at 375 px wide, with the keyboard, and with "reduce motion".
6. Its test next to it.

A new setting of the frontend is a `VITE_` variable: in the `environment` of the `frontend` service of `docker-compose.yml`, in the `env` of the frontend job of `ci.yml`, and checked in `checkSettings` of `vite.config.js`. Never in a `.env`.

## 6. The first module of the backend

Copy the shape of the demo (`modules/demo/` and `demo_router.py`), which stays in [the template's repository](https://github.com/davidcastillocruz/FastAPI-React-Template): it is the reference, file by file. The README's [*Adding a module*](README.md#adding-a-module) has the steps; in short:

1. **Model** in `src/modules/<module>/models/`, imported in `src/database/models.py`.
2. **Migration** with `alembic revision --autogenerate`, reviewed, and tried on an `app_check` database (`upgrade`, `alembic check`, `downgrade`, `upgrade`).
3. **Schemas**, **repository** (queries only, never a commit) and **service** (the logic, one commit at the end).
4. **Translations** of its messages and errors.
5. **Router** with one-line endpoints and a limit constant of `core/limiter.py`, registered in `main.py`.
6. **Tests**: its file, its rows in `test_limiter.py`, and a test that fails when each critical line is broken on purpose.

The first module makes the three tests of [section 2](#backend) pass. A first commit with all of this is a good point to stop and check that CI is green.

## 7. Working with Claude Code

[`CLAUDE.md`](CLAUDE.md) is read by Claude Code by itself when it starts in the repository. It is how the code gets written the same way every time: copy the closest case, ask before a new pattern, never commit without being told, prove every finding of a review.

Make it the project's:

1. Change its title and first paragraph to your project: what it is and for whom.
2. Add a `## This project` section: its modules, the decisions taken (with their reason), where its documentation and its design guide live.
3. Its `Example:` lines name files of the demo, which now only lives in the template's repository: the file says how to read them there. Once your own modules exist, say in `## This project` which of your files are the examples to copy.
4. When a new convention is settled, write it there in the same change. What isn't in the file doesn't reach the next session.
5. If it stops matching the code, the code wins and the file gets fixed.

Keep it committed, so everybody who works on the project (and every Claude session) works the same way.

## 8. Before calling a change done

```bash
docker compose up -d db redis
docker compose run --rm -T --no-deps backend sh -c 'ruff check . && pyright && pytest -q'
docker compose run --rm -T --no-deps frontend sh -c 'npx oxlint src && npm test && npm run build'
docker compose stop
```

And `alembic check` without changes when a model changed. CI runs the same on every push.

Once the project is set up, this file has done its job: delete it, with the *Starting a project* section of the README and its line in the README's *Project structure*.

## What the template doesn't give you

It is a **development** template. Before production you need, and have to decide: a production image and compose, a reverse proxy with HTTPS (and its IP in `FORWARDED_ALLOW_IPS`), a real mail provider, secrets out of the repository, backups of the database, and `APP_MODE=production`, which hides the API docs and enforces the production rules of `check_combinations`.
