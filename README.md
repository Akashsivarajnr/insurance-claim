# ClaimFlow - Insurance Claim Processing and Management System

A full-stack web application where customers submit insurance claims online and administrators review, verify, approve or reject them, then track settlement. Built as a Full Stack Development college project.

> **Please read:** this is a learning/demonstration project. It is **not production-ready** and is **not connected** to any real insurance company, bank or payment gateway. The settlement feature only *records* a date and a transaction reference typed in by an administrator; no money moves.

---

## 1. Problem statement

Insurance claim processing involves several manual verification stages. Paper or e-mail based handling causes delays, data-entry errors, lost documents and a lack of transparency: customers keep asking "where is my claim?" and staff have no single record of what happened and when.

## 2. Objectives

- Let customers submit claims and supporting documents online.
- Give administrators one place to verify documents and approve or reject claims.
- Enforce a valid workflow so claims cannot jump to impossible states.
- Keep a permanent history and notifications for every status change.
- Track approved amounts and settlement details.
- Show live statistics and reports calculated from the database.

## 3. Proposed solution

A React single-page application talks to a FastAPI REST backend. The backend stores data in SQLite through SQLAlchemy, protects every endpoint with JWT authentication and role checks, validates every input with Pydantic, and keeps uploaded documents in a private folder that is only reachable through authorised API endpoints.

## 4. Main features

**Customer:** register / log in / log out, personal dashboard, browse policy categories, submit a claim (policy, incident date, description, amount), upload PDF/JPG/PNG documents, receive a unique reference (e.g. `CF-2026-A1B2C3`), list and filter own claims, view status history, administrator comments and document requests, upload additional documents, view approved amount and settlement date/reference, notifications, edit profile.

**Administrator:** dashboard with statistics and charts, view all claims, search by reference or customer name, filter by status / type / submission date, open a claim, download and verify documents (or flag "Needs Information"), add comments, request documents, approve (with amount) or reject, manage settlement (Settlement Pending, Settled, date and transaction reference), customer list, reports and analytics.

**Workflow statuses:** Submitted, Under Review, Documents Required, Approved, Rejected, Settlement Pending, Settled.

| From | Allowed next status |
|---|---|
| Submitted | Under Review, Documents Required, Rejected |
| Under Review | Documents Required, Approved, Rejected |
| Documents Required | Under Review (also happens automatically when the customer uploads documents), Rejected |
| Approved | Settlement Pending |
| Settlement Pending | Settled |
| Rejected, Settled | none (final) |

Any other change is rejected by the backend with HTTP 409. Every change is stored in the claim history (previous status, new status, who, comment, time).

## 5. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, React Router, Axios, Recharts, lucide-react icons, plain CSS |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2, Uvicorn |
| Database | SQLite (single file, created automatically) |
| Security | JWT (python-jose), bcrypt password hashing, role-based access control, python-multipart for uploads |
| Testing | pytest + FastAPI TestClient (isolated temporary database) |

## 6. System architecture

```
 Browser (React, http://localhost:5173)
        |  Axios + JWT in Authorization header
        v
 FastAPI (http://localhost:8000)
   api/          route handlers (auth, policies, claims, admin, notifications)
   dependencies/ authentication + role checks
   schemas/      Pydantic request/response validation
   services/     workflow rules, uploads, notifications
   models/       SQLAlchemy tables
        |
        +--> SQLite file  backend/claimflow.db
        +--> private folder backend/uploads/   (never served as static files)
```

## 7. Database schema

| Table | Purpose and key columns |
|---|---|
| `users` | id, full_name, email (unique), hashed_password, phone, role (`customer` / `admin`), created_at |
| `insurance_policies` | id, policy_number (unique), policy_name, policy_type, coverage_amount, premium_amount, description, is_active |
| `claims` | id, claim_reference (unique), user_id -> users, policy_id -> insurance_policies, claim_type, incident_date, incident_description, requested_amount, approved_amount, status, admin_comments, submitted_at, updated_at, settlement_date, settlement_reference |
| `claim_documents` | id, claim_id -> claims, original_filename, stored_filename (random, unique), document_type, content_type, file_size, uploaded_at, verification_status, admin_comment |
| `claim_history` | id, claim_id -> claims, previous_status, new_status, changed_by -> users, comment, changed_at |
| `notifications` | id, user_id -> users, claim_id -> claims, message, is_read, created_at |

Relationships: a user has many claims and notifications; a policy has many claims; a claim has many documents and history rows (deleted together with the claim). Indexes exist on foreign keys, `email`, `claim_reference`, claim `status`, `claim_type`, `submitted_at`, and notification `(user_id, is_read)`. Tables are created automatically when the backend starts, and six sample policies are seeded when the policy table is empty. (`documents` and amounts use a few extra columns - `content_type`, `file_size` - beyond the minimum list.)

## 8. Project folder structure

```
insurance-claim-processing-system/
├── frontend/
│   ├── public/                  favicon
│   ├── src/
│   │   ├── api/client.js        Axios instance, error helper, document download
│   │   ├── components/          reusable UI (tables, badges, modals, uploader...)
│   │   ├── context/             AuthContext, ToastContext
│   │   ├── layouts/             PublicLayout, DashboardLayout (sidebar)
│   │   ├── pages/
│   │   │   ├── auth/            Login, Register
│   │   │   ├── customer/        dashboard, submit, my claims, details, notifications, profile
│   │   │   └── admin/           dashboard, claims, review, settlements, customers, reports
│   │   ├── routes/ProtectedRoute.jsx
│   │   ├── utils/format.js
│   │   ├── App.jsx, main.jsx, index.css
│   ├── .env.example, package.json, vite.config.js
├── backend/
│   ├── app/
│   │   ├── api/                 auth.py policies.py claims.py admin.py notifications.py
│   │   ├── core/                config.py (settings), security.py (hashing, JWT)
│   │   ├── dependencies/auth.py current user + role guards
│   │   ├── models/              SQLAlchemy tables
│   │   ├── schemas/             Pydantic models
│   │   ├── services/            claims.py (workflow), uploads.py, notifications.py
│   │   ├── database.py, seed.py, main.py
│   ├── tests/                   pytest suite (isolated test database)
│   ├── uploads/                 private document storage (.gitkeep only)
│   ├── create_admin.py          creates an administrator account
│   ├── seed_demo.py             optional demo customer + sample claims
│   ├── .env.example, requirements.txt, pytest.ini
├── screenshots/
├── README.md, .gitignore, start_project.bat
```

## 9. Installation prerequisites (Windows 10 / 11)

1. **Python 3.10 or newer** - download from <https://www.python.org/downloads/>. In the installer, **tick "Add python.exe to PATH"**. Check with `python --version` in Command Prompt.
2. **Node.js (LTS)** - download from <https://nodejs.org/>. Check with `node --version` and `npm --version`.
3. An internet connection for the first install (packages are downloaded).

## 10. Quick start (easiest)

1. Extract `insurance-claim-processing-system.zip` (right-click -> *Extract All*). Avoid extracting inside a protected folder such as `C:\Program Files`.
2. Open the extracted folder and **double-click `start_project.bat`**. It checks Python and Node.js, installs missing packages, creates `backend\.env` with a random secret (only if it does not already exist), and opens two windows (backend and frontend). Nothing is deleted or overwritten.
3. Create the administrator account (section 13), then open **http://localhost:5173**.

If the script fails, use the manual steps below.

## 11. Manual setup

Open **Command Prompt** (press Win, type `cmd`, Enter).

**Backend**
```bat
cd path\to\insurance-claim-processing-system\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

**Frontend** (a second Command Prompt window)
```bat
cd path\to\insurance-claim-processing-system\frontend
npm install
```

## 12. Environment variables

`backend\.env` (copied from `.env.example`):

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Secret used to sign login tokens. Replace the placeholder with a random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. If left as the placeholder, the app creates a temporary key each start (you will be logged out whenever the backend restarts). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Login lifetime, default 60 |
| `CORS_ORIGINS` | Allowed frontend addresses, default `http://localhost:5173,http://127.0.0.1:5173` |
| `MAX_UPLOAD_MB` | Maximum size per uploaded file, default 5 |
| `DATABASE_URL` | Optional; defaults to `backend/claimflow.db` |

`frontend\.env` is optional: set `VITE_API_URL` only if the backend is not at `http://localhost:8000`. **Never commit real `.env` files.**

## 13. Creating an administrator account

Administrators cannot self-register (the public registration form always creates customers). Create one from the command line:

```bat
cd backend
venv\Scripts\activate
python create_admin.py
```

It asks for an email, name and password (8-64 characters, letters and numbers). Or in one line:

```bat
python create_admin.py --email admin@claimflow.com --name "Demo Admin" --password "ChooseAStrongOne1"
```

Notes: the email must look like a real address - reserved endings such as `.local` or `.test` are rejected. Running the script again with an existing email promotes/updates that account, so it is safe to repeat. No default admin password is shipped with the project.

**Optional demo data** (so charts and tables are not empty), after creating the admin:

```bat
python seed_demo.py
```

This creates the customer `customer@claimflow.com` with password `Customer123` and six sample claims in different statuses. It is for local demos only.

## 14. Starting the application manually

Backend window:
```bat
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
Frontend window:
```bat
cd frontend
npm run dev
```

| What | URL |
|---|---|
| Application | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| **API documentation (Swagger UI)** | http://localhost:8000/docs |

The database file and tables are created automatically on first start.

## 15. Logging in

- **Customer:** click *Create account* on the website, or use `customer@claimflow.com` / `Customer123` if you ran `seed_demo.py`.
- **Administrator:** the account you created in section 13. After login, administrators are sent to `/admin`, customers to `/customer`; each role is blocked from the other's pages and API endpoints.

## 16. Suggested demo script for your lecturer

1. Register a customer, submit a Health claim with a PDF or image.
2. Note the reference number. Log out and log in as the administrator.
3. Open the claim -> *Start review* -> verify the document -> *Request documents* with a comment.
4. Log back in as the customer, see the request, upload another document (status returns to Under Review).
5. As administrator: *Approve* with an amount -> *Start settlement* -> *Record settlement* with a date and transaction reference.
6. As customer: view the history, approved amount and settlement details; check Notifications.
7. As administrator: open Reports and the dashboard charts.

## 17. Running the tests

```bat
cd backend
venv\Scripts\activate
python -m pytest
```

The tests use a temporary database and upload folder, so your real data is never touched. They cover registration/login, invalid credentials, claim submission and validation, ownership restrictions, admin-only endpoints, status transitions, approval and settlement, document upload validation and protected downloads, notifications, and dashboard statistics.

## 18. Security notes

- Passwords are hashed with bcrypt; JWTs expire; secrets come from `.env`.
- Every sensitive endpoint checks the logged-in user and role on the server; customers receive "not found" for other customers' claims and documents.
- Uploads: only PDF/JPG/JPEG/PNG, 5 MB limit, extension **and** file signature are checked, the server renames files to random names, filenames from users are never used as paths, and the `uploads` folder is **not** exposed as a static folder - files are downloaded through `/api/documents/{id}/download` after an authorisation check.
- **This upload feature is a demonstration.** Real insurance documents need much stronger production-grade storage and privacy controls (encryption at rest, virus scanning, audit logs, retention rules, cloud object storage with private access, regulatory compliance).

## 19. Known limitations and future enhancements

Limitations:
- SQLite and local file storage are for development only; amounts are stored as floating-point numbers (use fixed-point decimals for real money).
- No e-mail/SMS delivery: notifications are in-app only. No password reset, e-mail verification, two-factor login or login rate limiting.
- Only one administrator role (no separate reviewer/finance roles); administrators do not receive notifications about new claims.
- Policies are seeded sample products; customers choose a policy rather than purchasing one, and there is no check that the customer actually owns that policy.
- The JWT is stored in browser `localStorage` (simple, but exposed to script injection; production apps often use HTTP-only cookies).
- Automated tests cover the backend only; the React interface was built and API-route-checked but has no automated UI tests.
- No payment gateway: settlement is a record, not a transfer.

Future ideas: e-mail notifications, password reset, policy purchase and ownership, fraud-risk flags, audit export (CSV/PDF), PostgreSQL and cloud storage, Docker deployment, frontend tests with Vitest/Playwright, multi-role staff permissions.

## 20. Troubleshooting

- *"python is not recognised"*: reinstall Python and tick "Add python.exe to PATH".
- *"Cannot reach the server"* in the browser: the backend window is not running or is not on port 8000.
- *Port already in use*: close old ClaimFlow windows, or start the backend with `--port 8001` and set `VITE_API_URL=http://localhost:8001` in `frontend\.env` (and add the frontend address to `CORS_ORIGINS`).
- *Logged out after every restart*: set a real `SECRET_KEY` in `backend\.env`.
- *PowerShell blocks `venv\Scripts\activate`*: use Command Prompt (`cmd`), or run `venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
