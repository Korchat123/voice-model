# Paused work handoff — Docker and PostgreSQL

## Resume request

When work resumes, say:

> Resume the Docker/PostgreSQL work from `PAUSE-HANDOFF.md`. Inspect the dirty
> working tree first, finish validation, run the real Compose smoke test, then
> commit and push only when all checks pass.

## Last completed and pushed feature

- Commit: `1d1a6fb Guide users through safe local voice setup`
- Branch: `main`
- Remote: `origin`
- GitHub Actions passed for that commit.
- The guided UI is available at `/setup`.

## Current paused feature

Add a Docker Compose environment with:

- the existing local voice service;
- PostgreSQL for voice-profile, consent-state, controls, and reference-hash
  metadata;
- no recording bytes, model weights, secrets, or private datasets in the
  database;
- setup-UI support for explicitly saving a draft profile;
- real PostgreSQL integration and API smoke tests.

This feature is **unfinished, unvalidated, uncommitted, and unpushed**.

## Work already drafted

New container files:

- `.dockerignore`
- `Dockerfile`
- `compose.yaml`

New profile/database code:

- `src/voice_model/profiles/__init__.py`
- `src/voice_model/profiles/models.py`
- `src/voice_model/profiles/store.py`
- `src/voice_model/profiles/postgres.py`
- `src/voice_model/service/profile_routes.py`
- `scripts/migrate_database.py`
- `scripts/docker_database_smoke.py`

New tests:

- `tests/unit/profiles/test_models.py`
- `tests/contract/test_voice_profiles_api.py`
- `tests/integration/database/test_postgres_profiles.py`

Modified integration points:

- `pyproject.toml` adds Psycopg and a `database` pytest marker.
- `src/voice_model/service/settings.py` accepts `VOICE_DATABASE_URL`.
- `src/voice_model/service/app.py` selects PostgreSQL or in-memory storage and
  adds profile routes.
- `src/voice_model/ui/index.html` adds “Save profile to local database.”
- `src/voice_model/ui/app.js` posts the draft manifest to the profile API.
- `.env.example` documents the database URL.
- `README.md` contains preliminary Compose instructions.

## Intended API

- `POST /v1/voice-profiles`
- `GET /v1/voice-profiles`
- `GET /v1/voice-profiles/{profile_id}`
- `DELETE /v1/voice-profiles/{profile_id}`

The API accepts profile metadata only. Reference audio is represented by
filename, media type, byte size, and SHA-256. It must reject paths, audio bytes,
unknown controls, missing authorization attestation, oversized bodies, and
unsafe identifiers.

## Important current blocker

Docker CLI and Compose are installed, but the Docker engine was inaccessible:

```text
permission denied while trying to connect to the docker API at
npipe:////./pipe/docker_engine
```

There was also an access warning for:

```text
C:\Users\korch\.docker\config.json
```

On resume, confirm Docker Desktop is running. If access still fails, retry the
Docker commands with the execution environment’s required escalation.

## Validation not yet performed

The drafted PostgreSQL feature has not yet passed:

- dependency lock refresh;
- Ruff formatting and linting;
- strict mypy;
- unit/contract tests;
- full coverage gate;
- Compose configuration validation;
- Docker image build;
- live PostgreSQL migration;
- live create/get/list/delete smoke test;
- Docker cleanup and restart/persistence test;
- GitHub Actions.

Do not commit or push until these checks pass.

## Expected next commands

Use the workspace-local uv cache/interpreter locations on Windows:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
$env:UV_PYTHON_INSTALL_DIR='.uv-python'
uv lock
uv sync --frozen
uv run ruff format .
uv run ruff check .
uv run mypy
uv run python -m pytest --cov -q
node --check src/voice_model/ui/app.js
docker compose config
docker compose up --build -d
docker compose ps
uv run python scripts/docker_database_smoke.py
docker compose restart app
uv run python scripts/docker_database_smoke.py
docker compose down
```

Run the marked database test against the live container as well:

```powershell
$env:VOICE_TEST_DATABASE_URL='postgresql://voice_model:voice-model-local-only@127.0.0.1:5432/voice_model'
uv run python -m pytest -q -m database tests/integration/database
```

Do not run `docker compose down -v` unless intentionally deleting the local
database volume.

## Review points before validation

1. Confirm Psycopg async result and row typing passes strict mypy.
2. Confirm PostgreSQL `reference_metadata` handles SQL `NULL` with the explicit
   JSONB cast.
3. Confirm profile timestamps and upsert equality behave consistently.
4. Confirm Starlette lifespan migration failures make the service fail closed.
5. Confirm existing tests that instantiate `create_app()` remain isolated with
   the in-memory store.
6. Confirm the Docker image includes UI static assets and migration/runtime
   scripts.
7. Confirm Compose binds application and PostgreSQL ports to loopback only.
8. Add the real database test to an appropriate protected CI/Compose workflow
   after local validation.

## Commit policy

When complete, use a readable commit message such as:

```text
Test local voice profiles with Docker and PostgreSQL
```

Then push `main` and verify the resulting GitHub Actions run succeeds.
