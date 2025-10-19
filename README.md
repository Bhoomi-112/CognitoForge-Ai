# CognitoForge Labs

Repo housing both sides of the CognitoForge Labs hackathon project:

- **Backend** – FastAPI API that powers AI-driven DevSecOps simulations.
- **Frontend** – Next.js prototype for exploring mock attack reports.

---

## Backend (`backend/`)

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. (Optional) configure environment variables in `backend/.env`:
   ```env
   COGNITOFORGE_AUTH0_DOMAIN=https://your-auth0-domain
   COGNITOFORGE_AUTH0_CLIENT_ID=client-id
   COGNITOFORGE_GEMINI_API_KEY=gemini-key
   COGNITOFORGE_GEMINI_MODEL=gemini-1.5-flash
   COGNITOFORGE_SNOWFLAKE_ACCOUNT=account
   COGNITOFORGE_SNOWFLAKE_USER=user
   COGNITOFORGE_SNOWFLAKE_PASSWORD=password
   COGNITOFORGE_SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   COGNITOFORGE_SNOWFLAKE_DATABASE=COGNITOFORGE_DB
   COGNITOFORGE_SNOWFLAKE_SCHEMA=PUBLIC
   COGNITOFORGE_USE_GEMINI=false
   ```
   (See `backend/.env.example` for a ready-to-copy template.)
4. Launch the API server:
   ```bash
   uvicorn backend.app.main:app --reload
   ```

### Layout

- `backend/app/main.py` – FastAPI instance with CORS, health check, and router wiring.
- `backend/app/routers/operations.py` – REST endpoints for repository upload, attack simulation, reporting, and simulation history.
- `backend/app/services/` – Service layer stubs for Gemini, sandbox execution, and mock Snowflake queries.
- `backend/app/models/schemas.py` – Shared Pydantic models used across routers and services.
- `backend/app/data/vulnerabilities.json` – Mock vulnerability database seeded with three CVE examples.
- `backend/app/core/settings.py` – Environment-based configuration helper.

### Extending the stub

- Replace `backend/app/services/gemini_service.py` with real calls to the Gemini API once credentials are available.
- Wire the sandbox service to your containerised execution engine in `backend/app/services/sandbox_service.py`.
- Swap the mock Snowflake service with actual warehouse queries in `backend/app/services/snowflake_service.py`.

### Testing the endpoints

After starting the server, open the interactive docs at `http://127.0.0.1:8000/docs` to experiment with the mock endpoints.

Example curl workflow:

```bash
# Health check
curl http://127.0.0.1:8000/health

# Upload a repository reference
curl -X POST http://127.0.0.1:8000/upload_repo \
  -H "Content-Type: application/json" \
  -d '{"repo_id":"demo-repo","repo_url":"https://github.com/example/repo"}'

# Simulate an attack and persist the results
curl -X POST http://127.0.0.1:8000/simulate_attack \
  -H "Content-Type: application/json" \
  -d '{"repo_id":"demo-repo"}'

# Fetch the latest summary report for that repo
curl http://127.0.0.1:8000/reports/demo-repo/latest
```

Run `python backend/smoke_test.py` for an automated version of the same workflow.

---

## Frontend (`frontend/`)

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Configure Auth0 (optional) by copying the example env file:
   ```bash
   cp .env.local.example .env.local
   ```
3. Start the dev server:
   ```bash
   npm run dev
   # Open http://localhost:3000
   ```

### Layout

- `frontend/src/app/` – App Router pages and Auth0 routes.
- `frontend/src/components/` – UI, layout, auth, and feature components.
- `frontend/src/styles/` – Global styling helpers.

Refer to `docs/SETUP.md` and `docs/AUTH0_SETUP.md` for deeper frontend guidance.
