# NSS Connect

**AI-Powered Volunteer–NGO Matching & NSS Management Platform**
*Volunteer–NGO Matching & Verified ABP Tracking*

NSS Connect brings NGOs, NSS units, volunteers and college/university administrators onto one platform. NGOs are verified before they post drives. NSS units apply as a group. Students register individually and check in and out with a QR code. Certificates are generated automatically after verified participation and mandatory feedback. ABP 1 / ABP 2 hours are tracked separately.

| Layer | Stack |
|---|---|
| Frontend | React 18 · Vite · Tailwind CSS · React Router · Axios · Recharts · Leaflet + OpenStreetMap · React Hook Form · html5-qrcode |
| Backend | Django 5.1 · Django REST Framework · Simple JWT (rotation + blacklist) · django-cors-headers · ReportLab · qrcode · Pillow |
| Database | SQLite (development) · PostgreSQL (when `DATABASE_URL` is set) |

---

## 1. Quick start

**Fastest:** run `scripts\start.bat` (Windows) or `scripts/start.sh` (macOS/Linux). It creates `.env` with `DEBUG=True`, installs everything on first run, and starts both servers. If the site shows "Server offline", the Django API isn't running — check http://127.0.0.1:8000/api/health/.

Requirements: **Python 3.11+**, **Node 18+** (20/22 recommended). On Windows 10/11, use the `.bat` scripts.

```bash
# macOS / Linux
scripts/setup.sh        # venv, pip install, migrate, seed demo data, npm install
scripts/dev.sh          # Django :8000 + Vite :5173
```

```bat
:: Windows
scripts\setup.bat
scripts\dev.bat
```

Open **http://localhost:5173**. In development, verification and reset emails are printed in the Django console.

<details><summary>Manual setup</summary>

```bash
cp .env.example .env                  # set DEBUG=True for development
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo_data
python backend/manage.py runserver 0.0.0.0:8000

cd frontend && cp .env.example .env && npm install && npm run dev
```
</details>

### Demo accounts (password `NssDemo@2026`)

| Email | Role |
|---|---|
| admin@nssconnect.local | Super Admin (also a Django superuser, `/django-admin/`) |
| mu.admin@nssconnect.local | University Admin – University of Mumbai |
| sies.admin@nssconnect.local | College Admin – SIES College |
| coordinator.sies@nssconnect.local | NSS Coordinator (SIES unit, hosts today's live drive) |
| organizer@greenmumbai.org / organizer@sankalpblood.org | NGO Organizer (verified NGO) |
| organizer@akshar.org | NGO Organizer (NGO **pending** verification, cannot post) |
| aarav.mehta@student.nssconnect.local | Volunteer (4 certificates, approved for today's live drive) |
| diya.iyer@… rohan.patil@… sneha.kulkarni@… (all `@student.nssconnect.local`) | Volunteers |

`seed_demo_data` creates 10 volunteers, 3 NGOs, 3 NSS units, 10 events across all four categories, applications, attendance, hours, feedback, real certificate PDFs, notifications, a group application, an emergency request and AI recommendations. Past drives go through the real services (check-out → hours → feedback → certificate), so every dashboard number is computed from those rows. One drive, **Campus Cleanliness & Waste Audit**, runs *today, around the time you seed*, with an active QR code for a live check-in demo. Use `--reset` to wipe and reseed.

---

## 2. Mobile access without the same Wi-Fi (Section 53)

The frontend calls the API at the relative path `/api`. In development, Vite proxies `/api` and `/media` to Django. In production, Django serves the built React app itself. Either way the browser sees **one origin**, so **one HTTPS tunnel URL exposes the whole app**, including login cookies, API, uploads and QR links. Phones need HTTPS for the in-browser camera scanner, and tunnels provide it.

### Option A: Cloudflare quick tunnel (free, no account)

```bash
scripts/dev.sh                 # terminal 1
scripts/share-mobile.sh        # terminal 2  → prints https://<random>.trycloudflare.com
```

Install `cloudflared` from the Cloudflare downloads page, or on Windows with `winget install --id Cloudflare.cloudflared`. Open the printed URL on any phone, on mobile data or any Wi-Fi.

* QR codes generated from that browser automatically encode the tunnel URL (the backend uses the request `Origin`). No config change is needed. To pin a URL, set `FRONTEND_URL`.
* `DEBUG=True` already allows `*.trycloudflare.com` and `*.ngrok-free.app` hosts.

### Option B: ngrok

`ngrok http 5173` (Vite) or `ngrok http 8000` (production build). Then add the ngrok host to `ALLOWED_HOSTS` when `DEBUG=False`.

### Option C: production-style single server + tunnel

```bash
# .env: DEBUG=False, SECRET_KEY=..., ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
scripts/serve-prod.sh          # builds React, collectstatic, gunicorn on :8000 (Windows: serve-prod.bat → waitress)
scripts/share-mobile.sh 8000
```

With `DEBUG=False` the refresh cookie is `Secure`, which is correct behind an HTTPS tunnel. For plain-HTTP testing on `localhost`, set `JWT_COOKIE_SECURE=False`.

### Option D: same Wi-Fi (no tunnel)

Vite listens on the LAN (`host: true`), so `http://<laptop-ip>:5173` works. The camera scanner needs HTTPS, so on this option scan the QR with the phone's own camera app, which opens the check-in link.

### Real hosting

Deploy the backend with `DATABASE_URL` (PostgreSQL), `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, SMTP settings and HTTPS (`SECURE_SSL_REDIRECT`/`SECURE_HSTS_SECONDS` if Django terminates TLS). Build the frontend (`npm run build`) and either let Django serve `frontend/dist` or host it separately. For a separate host, set `VITE_API_URL=https://api.example.com/api`, `CORS_ALLOWED_ORIGINS`, `JWT_COOKIE_SAMESITE=None`.

---

## 3. The complete workflow (Section 50)

1. **Register** (`/register`). The account is created, the password is hashed, and a verification email is sent.
2. **Verify email** (`/verify-email?uid=…&token=…`). The token is a signed one-time token.
3. **Log in**. You get a JWT access token (held in memory) and a refresh token in an **httpOnly cookie** (never in localStorage).
4. **Dashboard** (`/dashboard`). Stats come from `/api/dashboard/volunteer/`, which uses ORM queries.
5. **Browse** (`/events`). Server-side filters: `?category=ABP1&search=&date=&location=&skill=&available=true`, with cards, map and calendar views.
6. **Register for a drive**. `POST /api/events/{id}/register/` creates an `EventApplication` (a DB unique constraint blocks duplicates, and a full drive puts you on the waitlist).
7. **Organizer approves** (`/events/{id}/applications`). `POST /api/applications/{id}/approve/` checks capacity, then creates a notification and an email.
8. **Event QR** (`/events/{id}/attendance`). `POST /api/events/{id}/qr/` creates a random 43-character token URL with no personal data. It expires after the event and rotates on regeneration.
9. **Scan**. Use `/scan` (in-app camera) or any camera app to open `/attendance/check-in/<token>`.
10. **Check-in**. `POST /api/attendance/check-in/` runs the backend checks: auth, token valid/active/unexpired, event approved/ongoing, registered, application approved, time window, and no duplicate (also enforced by a DB constraint). The volunteer is marked PRESENT, or LATE after 15 minutes.
11. **Check-out** (at least 15 minutes later). Hours are calculated as `check_out − check_in`, capped at the scheduled duration, and a `VolunteerHours` row is stored with *unverified* status.
12. **Mandatory feedback**. `POST /api/events/{id}/feedback/` marks the hours verified, the application COMPLETED, and generates the **certificate PDF** (ReportLab + verification QR).
13. **Certificate in dashboard**. The certificate appears in `/certificates`, with PDF download through an authenticated endpoint.
14. **Public verification**. `/certificate/<ID>/verify` calls `GET /api/certificates/<ID>/verify/` and shows only what is printed on the certificate.
15. **Analytics update**. `/analytics` is recomputed on every request.

Organizers can **complete** a drive. That auto-checks-out anyone still checked in (at the scheduled end), marks no-shows ABSENT, deactivates QR codes and writes the post-event summary.

---

## 4. AI features (honest scope)

Everything runs offline through `AIProvider` → `RuleBasedAIProvider` (`backend/ai_matching/providers.py`). **None of it is a trained ML model**, and the UI and API responses say so with a disclaimer.

| Feature | Endpoint | Method |
|---|---|---|
| NSS-unit recommendation | `GET /api/events/{id}/recommendations/` | Weighted score: distance 25%, skills 20%, availability 20%, historical attendance 20%, interest/category 15%. Weights are configurable via `AI_MATCH_WEIGHTS`. Stored in `AIRecommendation`, with per-component scores and human-readable reasons. |
| Category suggestion | `POST /api/ai/categorize/` | Keyword rules → theme (Environment / Community → ABP 1; Health / Education / Awareness → ABP 2), plus college/university hints. Returns the matched keywords. |
| Turnout estimate | `GET /api/events/{id}/turnout-estimate/` | Approved registrations × historical show-up rate for the category, falling back to the overall rate and then a stated default. |
| Best date/time | `GET /api/ai/suggest-datetime/?category=` | Attended ÷ approved per weekday × time slot over completed events. |
| Post-event summary | `POST /api/events/{id}/summary/` | Template from attendance, hours, ratings, colleges and organizer notes. |

`AI_PROVIDER=openai` or `gemini` (with an API key) routes only the two text tasks (categorization and summary) to the LLM and falls back to the rules on any error. The app never requires an external AI API.

---

## 5. Roles & permissions (enforced server-side)

| Role | Can |
|---|---|
| VOLUNTEER | Browse, register/cancel, check in/out, give feedback, upload gallery photos for attended drives, download own certificates |
| NGO_ORGANIZER | Register an NGO and upload documents. Once **verified**: create drives (they start PENDING), manage own drives, applications, QR codes, attendance, group applications, emergency requests and AI tools |
| NSS_COORDINATOR | Register an NSS unit. Once verified: host college drives, apply to drives as a group, view members |
| COLLEGE_ADMIN | Approve/reject drives and verify NSS units **for their college**; view reports in scope |
| UNIVERSITY_ADMIN | The same for their university, plus NGO-hosted drives, and **verify/reject/suspend NGOs** |
| SUPER_ADMIN | Everything, including role changes and suspending admins |

Admin roles are assigned by a super admin in `/admin/users`. The frontend route guards are UX only: every rule lives in DRF views and `core/permissions.py`, including object-level checks.

---

## 6. API overview

```
Auth            POST /api/auth/register|login|logout|token/refresh|verify-email|resend-verification|forgot-password|reset-password|change-password/
                GET|PATCH /api/auth/profile/   POST|DELETE /api/auth/profile/photo/   GET /api/auth/google/config/  POST /api/auth/google/
Events          GET|POST /api/events/   GET|PUT|PATCH|DELETE /api/events/{id}/
                POST /api/events/{id}/approve|reject|set-status|register|cancel|group-apply|invite-unit/
                GET /api/events/{id}/applications|group-applications|photos/   GET /api/events/calendar|map|skills/
Applications    GET /api/applications/   POST /api/applications/{id}/approve|reject|waitlist/   POST /api/group-applications/{id}/accept|reject/
Attendance      GET|POST /api/events/{id}/qr/   POST /api/attendance/check-in|check-out/   GET /api/attendance/scan-status/?token=
                GET /api/events/{id}/attendance/   POST /api/events/{id}/attendance/mark-absent/   GET|POST /api/events/{id}/feedback/   GET /api/attendance/
Certificates    GET /api/certificates/   GET /api/certificates/{pk}/download/   GET /api/certificates/{certificate_id}/verify/ (public)
NGOs            CRUD /api/ngos/   POST /api/ngos/{id}/verify|reject|suspend/   GET|POST /api/ngos/{id}/documents/   POST /api/documents/{id}/review/
NSS             /api/universities/  /api/colleges/  CRUD /api/nss-units/  POST /api/nss-units/{id}/verify|reject|suspend/  GET /api/nss-units/{id}/members|stats/
AI              see section 4
Analytics       GET /api/analytics/ (public aggregates)   GET /api/dashboard/volunteer|organizer|admin/
Reports         GET /api/reports/?type=volunteer_participation|event_participation|abp1|abp2|attendance|volunteer_hours|college|university&export=csv|pdf|json
Notifications   GET /api/notifications/   POST /api/notifications/{id}/read/   POST /api/notifications/read-all/
Emergency       GET|POST /api/emergency-requests/
Health          GET /api/health/
```

Reports use `?export=` rather than `?format=`, because DRF reserves `format` for content negotiation.

---

## 7. Security notes

* PBKDF2 password hashing (Django default) and Django password validators.
* JWT access tokens last 30 minutes. Refresh tokens last 7 days, are rotated and blacklisted on use and on logout, sit in an httpOnly SameSite cookie scoped to `/api/auth/`, and are all revoked when an account is suspended.
* Rate limits: anonymous, user, auth endpoints (`20/min`) and check-in (`30/min`), all configurable.
* Uploads are checked for extension allow-list, size, declared MIME type, real content (Pillow `verify()` for images, `%PDF-` magic for PDFs) and blocked executable/archive signatures, and get random UUID file names. NGO documents and certificate PDFs are **not** publicly served; they go through authenticated endpoints.
* CSV export neutralizes spreadsheet formula injection.
* Security headers: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, secure cookies when `DEBUG=False`, optional HSTS/SSL redirect. No secret is hard-coded, and a missing `SECRET_KEY` with `DEBUG=False` refuses to start.
* Session auth (CSRF-enforced) exists only in DEBUG for the browsable API. In production the API is JWT-only.

---

## 8. Tests

```bash
cd backend && python manage.py test tests        # 72 tests, incl. the full Section 50 workflow
cd frontend && npm test                          # vitest: utils, API helpers, components
```

The backend tests cover registration, email verification, login and refresh rotation, logout blacklisting, password reset, suspension, profile and upload validation, the permission matrix and admin scoping, event CRUD and approval, server-side filters and pagination, registration, duplicate prevention (API and DB constraint), cancellation and re-registration, approve/reject/waitlist and capacity, group applications, emergency broadcast, QR generation and rotation, every check-in rule, duplicate check-in, check-out and hours capping, mandatory feedback, certificate PDF and public verification, event close-out, analytics (including "updates automatically"), dashboards, CSV/PDF reports, and all AI features. `tests/test_workflow.py` runs the complete workflow through the public API.

---

## 9. Other commands

```bash
python backend/manage.py seed_demo_data --reset      # wipe DB + reseed
python backend/manage.py send_event_reminders        # reminders for tomorrow's drives (schedule daily via cron/Task Scheduler)
python backend/manage.py createsuperuser             # email-based login
```

Django admin is at **`/django-admin/`**, because `/admin` belongs to the React admin panel. All models are registered with search, filters and bulk verify/approve actions.

## 10. Project layout

```
backend/
  config/            settings (env-driven), urls (API + SPA fallback)
  core/              permissions & admin scoping, upload validators, utils, seed_demo_data
  accounts/          User (email login, roles), UserProfile, VolunteerProfile, auth & admin-user APIs
  nss_units/         University, College, NSSUnit
  ngos/              NGO, VerificationDocument
  events/            Event, EventSkill, EventApplication, GroupApplication, EventPhoto, EmergencyVolunteerRequest
  attendance/        EventQR, Attendance, VolunteerHours, Feedback + business rules (services.py)
  certificates/      Certificate + ReportLab PDF generation
  notifications/     Notification + notify()/email service
  ai_matching/       AIProvider abstraction, RuleBased/OpenAI/Gemini providers, AIRecommendation
  analytics/         analytics, dashboards, CSV/PDF reports
  tests/             API test suite
frontend/src/
  services/          api.js (axios + refresh), authService, eventService, ngoService, nssService, applicationService,
                     attendanceService, certificateService, analyticsService, notificationService, adminService
  context/           AuthContext, ToastContext
  components/        Layout, ProtectedRoute, EventCard, MapView (Leaflet/OSM), CalendarView, QRScanner, ui primitives
  pages/             all routes from Section 43 (+ /scan, /calendar, /ngos/new, /events/new|:id/edit)
scripts/             setup / dev / share-mobile (tunnel) / serve-prod – .sh and .bat
```

## Pre-launch checklist (frontend)

Set these in `frontend/.env` before running `npm run build`:

| Variable | Purpose |
| --- | --- |
| `VITE_SITE_URL` | Public URL – used for `sitemap.xml`, `robots.txt`, canonical and social-preview URLs |
| `VITE_GA_ID` | Optional GA4 ID (`G-XXXXXXXXXX`); loads only after the visitor accepts cookies |
| `VITE_CONTACT_EMAIL` | Shown on the landing FAQ, Privacy Policy and Terms |

Open the folder in VS Code and run the tasks **Frontend: install** then **Frontend: dev server** (Terminal → Run Task).
The Privacy Policy and Terms are starter templates – have them reviewed before launch.
