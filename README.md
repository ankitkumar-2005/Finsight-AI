# FinSight – AI Finance Manager

FinSight combines a React/Vite dashboard, Flask REST API, MySQL persistence, and a separate Pandas/NumPy/scikit-learn analysis module. The visual identity is a premium black and purple finance workspace.

## Installation guide

Prerequisites: Node.js 20+, Python 3.11+, and MySQL 8.0+.

1. Install frontend dependencies: `npm install`.
2. In MySQL Workbench as an administrator, run `backend/setup_app_user.sql` after replacing both `REPLACE_WITH_A_STRONG_PASSWORD` values with a unique local password. Then run `backend/schema.sql`. This creates the application and disposable test databases, least-privilege account, and schema.
3. Copy `backend/.env.example` to `backend/.env`. Set `MYSQL_PASSWORD`, use a long random `FLASK_SECRET_KEY`, and keep `FLASK_ENV=development` only for local development. Never commit `.env`.
4. Install and run the backend:

   ```powershell
   python -m venv backend/.venv
   .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   .\backend\.venv\Scripts\python.exe backend/run.py
   ```

5. In a second terminal run `npm run dev`, then open the Vite URL (usually `http://localhost:5173`). Vite proxies `/api` to Flask on port 5000.

For production, build with `npm run build`, serve `dist/` from a static host, deploy Flask behind HTTPS, configure an allowlisted `CORS_ORIGINS` if frontend and API use different origins, and point `VITE_API_BASE_URL` at the API prefix. Set `FLASK_ENV=production`, `FLASK_DEBUG=0`, a strong secret, secure cookie settings, and `DEMO_RESET_MODE=0`. Configure an email provider before enabling real password-reset delivery; the project currently has no email integration.

## Project architecture

```text
src/                         React application and pages
  App.jsx                    Landing, routes, and shared toast
  pages/FinanceApp.jsx        Authenticated shell and finance pages
  pages/AnalyticsPage.jsx     Filtered charts and CSV download
  pages/BudgetsPage.jsx       Monthly budgets and alerts
  lib/api.js                  Credentialed API client
backend/finsight/            Flask routes, auth, SQL access, validation
backend/finsight_ai/          Independent transaction analysis module
backend/tests/                Unit tests and opt-in MySQL integration tests
backend/schema.sql            MySQL application schema
backend/setup_app_user.sql    Local app/test DB and least-privilege grants
```

The frontend calls the Flask API using same-origin session cookies. Flask scopes financial queries by the authenticated session user ID. The AI module receives that user's transaction rows as input and has no database connection of its own.

## Database schema

`users` stores unique normalized email addresses and Werkzeug scrypt password hashes. `financial_profiles` stores currency and goals by user. `password_reset_tokens` stores hashed one-use reset tokens with expiry. `transactions` stores per-user income/expense records with amount, category, payment type, date, and description. `monthly_budgets` stores one amount per user/category/month. Foreign keys cascade on user deletion. Amounts use `DECIMAL(12,2)` and transaction/date indexes support common queries.

## API documentation

All private routes require the HTTP-only Flask session cookie.

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create account and start session |
| POST | `/api/auth/login` | Authenticate and start session |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/forgot-password` | Prepare one-time reset token (demo token only in local development) |
| POST | `/api/auth/reset-password` | Consume reset token and update hash |
| GET/PUT | `/api/profile/me` | Read/update currency and savings profile |
| GET/POST | `/api/transactions` | Filter/search/list or create transactions |
| PUT/DELETE | `/api/transactions/{id}` | Update/delete own transaction |
| GET | `/api/dashboard/summary` | Aggregated personal dashboard figures |
| GET/PUT/DELETE | `/api/budgets?month=YYYY-MM` | List, upsert, or remove own category budgets |
| GET | `/api/analytics?range=...` | Analytics for preset or custom date ranges |
| GET | `/api/analytics/export?range=...` | CSV of transactions in selected range |
| GET | `/api/ai-insights` | User-specific comparisons, suggestions, outliers, and forecast |
| GET | `/api/health` | API process health (does not verify DB readiness) |

Transaction filters accept `type`, `category`, `q`, `date_from`, `date_to`, `sort_by`, and `sort_dir`. Analytics ranges: `last_7_days`, `last_30_days`, `this_month`, `last_month`, or `custom` with ISO `date_from` and `date_to`. Amounts are validated server-side; SQL values use parameterized queries.

## Testing report

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

The suite covers password/registration validation, route access control, budget calculations, date range validation, AI forecast math and history limits, savings comparisons, outlier explanations, and input handling. The current automated run passed 17 tests; the MySQL integration suite was skipped because `MYSQL_TEST_DATABASE` is not configured. To run database persistence and API integration checks, set `MYSQL_TEST_DATABASE=finsight_test` in the shell and run the same command. The integration tests create isolated users and real sample transactions, including AI per-user isolation.

Frontend production build: `npm run build` (verified). Browser/device visual QA and live database end-to-end QA have not been completed in this environment. This report does not mark those checks as passed.

## Known limitations and future scope

- Live MySQL service credentials are local setup; no database-backed login, CRUD, analytics, budget, export, or AI endpoint run was verified here.
- Forecasts are a linear trend with limited history, not guaranteed predictions or financial advice. Four monthly periods are required; confidence is limited and reported with mean absolute error.
- Spending categories use keyword matching against user-defined category names; unmatched labels do not appear in the named Food, Shopping, Travel, Entertainment, or Bills groups.
- Unusual-spend flags require at least five transactions in a category and use an IQR threshold. They are statistical prompts, not fraud detection.
- Password reset is a development demo flow until an email provider is configured.
- Planned work: browser automation across viewport sizes, email reset delivery, stronger category mapping, model backtesting, deployment automation, and optional opening-balance/transfer support.
