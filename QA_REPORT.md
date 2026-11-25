# FinSight Phase 6 QA Report

Date: 2026-11-25

## Verified in this workspace

- Frontend: `npm run build` completed successfully after QA cleanup.
- Backend unit suite: 17 tests passed. One MySQL integration suite was skipped because `MYSQL_TEST_DATABASE` is not configured.
- Python source: `compileall` completed successfully.
- Flask app factory: `/api/health` returned 200 and unauthenticated `/api/ai-insights` returned 401 in a test app.
- ML module: verified four months of sample values produce a 500.00 linear trend estimate, and test cases cover insufficient history, period comparisons, recommendation math, malformed values, and outlier explanations.
- `git diff --check` reported no whitespace errors.
- Source review confirmed scrypt password hashes, hashed one-time reset tokens, session-based authorization, user-scoped data queries, and bound SQL parameters.

## Not verified

- Live MySQL connectivity, schema persistence, registration/login/logout, duplicate-email behavior, CRUD ownership, budgets, analytics, CSV, and the AI endpoint with real database rows. The integration test suite is designed for these checks, but was skipped without a configured disposable MySQL database.
- Browser-driven interaction coverage for every control or screenshots. The local browser preview request timed out in the available browser environment. No screenshots are included because none could be captured and verified.
- Desktop, laptop, tablet, and mobile visual inspection. Responsive styles exist and the production build passes, but visual QA is still pending.
- Production deployment, TLS, real password reset email, and hosted service health.

## Security review notes

- Password storage uses Werkzeug scrypt; reset token values are hashed before storage and expire/are one-time.
- Finance endpoints use the session user ID and data queries reviewed in the route modules are scoped to that ID.
- SQL values use MySQL connector placeholders; dynamic sort SQL is selected only from a fixed allowlist.
- Configuration reads secrets from environment/.env; `.env` is ignored by git.
- Local demo reset mode exposes a reset token only while Flask debug and `DEMO_RESET_MODE` are enabled. Disable both in production.
- A global exception handler returns generic errors; logs may contain diagnostic details and must remain private.

## Functional surface review

Static source review found working handlers/routes for landing navigation and pricing preview, signup/login/password reset forms, protected dashboard navigation/logout, transaction create/edit/delete/search/filter/sort, budget create/edit/delete and month selection, analytics date ranges/charts/export, AI insights loading/retry, savings goal updates, and settings updates. These interactions are not equivalent to browser or live-database execution; see the unverified list above.

## Required before release

1. Configure MySQL using `backend/setup_app_user.sql`, create `backend/.env`, and run the persistence suite with `MYSQL_TEST_DATABASE=finsight_test`.
2. Run browser automation or manual checks at desktop, laptop, tablet, and phone viewport sizes. Capture screenshots only after rendering is verified.
3. Exercise full authentication and finance flows against the disposable database, including CSV contents and second-user isolation.
4. Set production secrets, HTTPS, secure cookies, CORS origins, and `DEMO_RESET_MODE=0`; integrate and test an email provider for password resets.
