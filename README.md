# CognitoForge Labs Backend

FastAPI skeleton for the CognitoForge Labs hackathon project (AI-driven DevSecOps red team simulator).

## Quick start

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) configure environment variables in a `.env` file:
   ```env
   COGNITOFORGE_AUTH0_DOMAIN=https://your-auth0-domain
   COGNITOFORGE_AUTH0_CLIENT_ID=client-id
   COGNITOFORGE_GEMINI_API_KEY=gemini-key
   COGNITOFORGE_SNOWFLAKE_ACCOUNT=account
   COGNITOFORGE_USE_GEMINI=false
   ```
4. Launch the API server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project layout

- `app/main.py` – FastAPI instance with CORS and router wiring.
- `app/routers/operations.py` – REST endpoints for repository upload, attack simulation, and report fetching.
- `app/services/` – Service layer stubs for Gemini, sandbox execution, and mock Snowflake queries.
- `app/models/schemas.py` – Shared Pydantic models used across routers and services.
- `app/data/vulnerabilities.json` – Mock vulnerability database seeded with three CVE examples.
- `app/core/settings.py` – Environment-based configuration helper.

## Extending the stub

- Replace `app/services/gemini_service.py` with real calls to the Gemini API once credentials are available.
- Wire the sandbox service to your containerised execution engine in `app/services/sandbox_service.py`.
- Swap the mock Snowflake service with actual warehouse queries in `app/services/snowflake_service.py`.

## Testing the endpoints

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

Run `python smoke_test.py` for an automated version of the same workflow.
