NSS Connect

## AI-Powered Volunteer–NGO Matching & NSS Management Platform
**NSS Connect** is a web-based platform that connects NGOs, NSS units, volunteers, and college/university administrators in one system. The platform supports verified NGO participation, NSS event management, volunteer registration, QR-based attendance, ABP hour tracking, feedback, certificate generation, reporting, maps, notifications, and rule-based volunteer–NGO matching.
> **Academic Project:** Third-Year College Project
---

## 1. Project Overview
NSS Connect is designed to simplify and digitize the management of NSS and community-volunteering activities.
The platform provides a structured workflow in which:
- NGOs can register and undergo verification before publishing drives.
- NSS units can register and participate in drives as groups.
- Volunteers can discover events, register, attend, and track participation.
- QR-based check-in/check-out helps record attendance.
- ABP 1 and ABP 2 hours are tracked separately.
- Mandatory feedback is collected after participation.
- Certificates can be generated after verified participation.
- Administrators can manage users, organizations, events, approvals, and reports.
- Event locations can be displayed using maps.
- Rule-based matching can recommend suitable opportunities for volunteers/NSS units.
---

## 2. Objectives
1. Digitize NSS and volunteer event management.
2. Connect verified NGOs with volunteers and NSS units.
3. Reduce manual attendance and record-keeping.
4. Provide reliable ABP 1 and ABP 2 hour tracking.
5. Automate participation certificate generation.
6. Provide dashboards and reports for administrators.
7. Improve transparency through approval and verification workflows.
8. Provide event location and map-based information.
9. Provide rule-based recommendations for suitable events.
10. Maintain role-based access and secure authentication.
---

## 3. Main Modules

### Authentication & User Management
- Email-based registration and login
- Email verification
- Password reset/change
- Role-based permissions
- User profiles and profile photos

### Volunteer Management
- Browse available drives
- Search and filter events
- Register/cancel participation
- Check in and check out
- Submit feedback
- Track participation and volunteer hours
- Download certificates

### NGO Management
- NGO registration
- Verification documents
- Verification/rejection/suspension workflow
- Event creation and management
- Volunteer application management

### NSS Unit Management
- University and college structure
- NSS unit registration
- NSS unit verification
- Group applications
- Member and participation tracking

### Event Management
- Event creation
- Event approval
- Categories and skills
- Capacity management
- Applications and waitlists
- Event calendar
- Event map/location support
- Event photos
- Emergency volunteer requests

### QR Attendance
- Event-specific QR codes
- QR check-in
- Check-out
- Duplicate prevention
- Attendance status
- Volunteer hour calculation

### Feedback & Certificates
- Mandatory post-event feedback
- Verified volunteer hours
- Automatic certificate generation
- Certificate verification

### Analytics & Reports
- Volunteer participation
- Event participation
- Attendance
- ABP 1/ABP 2 hours
- College and university reports
- CSV/PDF/JSON reporting

### Notifications
- Application updates
- Event-related notifications
- Administrative notifications
- Event reminders

### Matching & AI-Assisted Features
The current project uses an offline rule-based provider by default. It is **not presented as a trained machine-learning model**.
Features include:
- Volunteer/NSS-unit event recommendations
- Category suggestions
- Turnout estimates
- Date/time suggestions
- Post-event summaries
Optional external AI providers may be configured separately during development/deployment. API credentials must never be committed to this repository.
---

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Router, Axios, Recharts |
| Maps | Leaflet + OpenStreetMap |
| Forms | React Hook Form |
| QR | html5-qrcode |
| Backend | Django 5.1, Django REST Framework |
| Authentication | JWT with refresh-token rotation/blacklisting |
| Security | django-cors-headers, Django password hashing/validation |
| PDF | ReportLab |
| QR Generation | qrcode |
| Image Processing | Pillow |
| Database | SQLite for development, PostgreSQL for production |
---

## 5. System Architecture

```text
                 ┌──────────────────────────┐
                 │       React Frontend     │
                 │  Vite + Tailwind + Axios │
                 └────────────┬─────────────┘
                              │
                              │ REST API
                              ▼
                 ┌──────────────────────────┐
                 │      Django Backend      │
                 │      Django REST API     │
                 └────────────┬─────────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       Authentication     Business Logic    Reporting
       & Permissions      & Workflows       & Analytics
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    ┌──────────────────┐
                    │     Database     │
                    │ SQLite/Postgres  │
                    └──────────────────┘
```
---

## 6. Core Workflow

```text
Register
   ↓
Email Verification
   ↓
Login
   ↓
Browse Events
   ↓
Register for Event
   ↓
Application Approval
   ↓
Event QR Check-in
   ↓
Check-out
   ↓
Volunteer Hours Calculation
   ↓
Mandatory Feedback
   ↓
Verified Participation
   ↓
Certificate Generation
   ↓
Dashboard / Reports
```
---

## 7. Roles

| Role | Main Responsibilities |
|---|---|
| Volunteer | Browse events, register, attend, provide feedback, view hours and certificates |
| NGO Organizer | Manage NGO profile, events, applications, attendance and related activities |
| NSS Coordinator | Manage NSS unit participation and group applications |
| College Admin | Manage college-level approvals, NSS units and reports |
| University Admin | Manage university-level administration and NGO verification workflows |
| Super Admin | System-wide administration and role management |
All important permissions are enforced on the backend. Frontend route guards are not treated as the only security mechanism.
---

## 8. Project Structure

```text
NSS-Connect/
│
├── backend/
│   ├── manage.py
│   ├── config/
│   ├── core/
│   ├── accounts/
│   ├── nss_units/
│   ├── ngos/
│   ├── events/
│   ├── attendance/
│   ├── certificates/
│   ├── notifications/
│   ├── ai_matching/
│   ├── analytics/
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── services/
│   │   ├── context/
│   │   ├── components/
│   │   └── pages/
│   └── public/
│
├── scripts/
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```
---

## 9. Development Requirements
- Python 3.11+
- Node.js 18+
- npm
- Git
- A modern web browser
- SQLite for simple development, or PostgreSQL for production
---

## 10. Local Installation

### Backend

```bash
python -m venv .venv
```
Windows:

```bat
.venv\Scripts\activate
```
macOS/Linux:

```bash
source .venv/bin/activate
```
Install dependencies:

```bash
pip install -r backend/requirements.txt
```
Run migrations:

```bash
python backend/manage.py migrate
```
Start Django:

```bash
python backend/manage.py runserver
```
### Frontend
Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```
Then open the local development URL shown by Vite.
> Keep environment-specific values in local `.env` files. Do not commit `.env` files containing real secrets.
---

## 11. Environment Configuration
Create local environment files from the provided examples.
Example backend variables:

```env
DEBUG=True
SECRET_KEY=replace-with-a-local-secret
DATABASE_URL=replace-with-your-database-url
```
Example frontend variables:

```env
VITE_SITE_URL=http://localhost:5173
VITE_CONTACT_EMAIL=your-email@example.com
```
Only use real API keys, passwords, database credentials, email credentials, or production secrets in local/deployment environment configuration.
---

## 12. Security
The project includes security-oriented features such as:
- Django password hashing and validation
- JWT authentication
- Refresh-token rotation and blacklisting
- HTTP-only refresh cookies
- Role-based access control
- Backend permission checks
- Upload validation
- File type and size validation
- Protection against duplicate attendance
- Secure production cookie configuration
- Security headers
- Spreadsheet formula-injection protection for CSV exports
- Environment-based secret configuration

### Important GitHub rule
**Never commit:**

```text
.env
database passwords
Django SECRET_KEY
JWT secrets or tokens
API keys
SMTP passwords
cloud credentials
private deployment credentials
real user personal information
```
If a secret has already been pushed to GitHub, rotate/revoke it. Simply deleting it from the latest README does not make an exposed secret safe.
---

## 13. Testing
The project contains backend and frontend tests covering important workflows such as:
- Authentication
- Registration and verification
- Permissions
- Event management
- Applications
- Attendance
- QR workflows
- Volunteer hours
- Feedback
- Certificates
- Reports
- Analytics
- Matching features
Run backend tests with:

```bash
cd backend
python manage.py test
```
Run frontend tests using the project's configured npm test command.
---

## 14. Future Scope
Possible future enhancements include:
- Native Android/iOS application
- Advanced machine-learning recommendation models
- Push notifications
- Cloud storage for approved documents
- Advanced geospatial matching
- Institution-wide deployment
- Improved accessibility
- More detailed analytics
- Integration with additional university/NSS systems
- Production-grade monitoring and audit logging
---

## 15. Academic Value
This project demonstrates practical implementation of:
- Full-stack web development
- REST API development
- Database design
- Authentication and authorization
- Role-based access control
- QR technology
- Map integration
- PDF generation
- Reporting and analytics
- Software testing
- Secure configuration management
- User-interface design
- Business workflow automation
---

## 16. Suggested Screenshots for the Repository
For a college project repository, screenshots can be placed in:

```text
docs/screenshots/
```
Suggested screenshots:
1. Home/Landing page
2. Login page
3. Volunteer dashboard
4. Event listing
5. Event details
6. Map/event location
7. NGO dashboard
8. NSS coordinator dashboard
9. QR attendance screen
10. Feedback screen
11. Certificate screen
12. Analytics/report dashboard
13. Admin dashboard
Do not include screenshots containing passwords, API keys, tokens, personal documents, or private user information.
---

## 17. Project Limitations
- The default matching functionality is rule-based rather than a trained ML model.
- Some production services require environment-specific configuration.
- Development uses SQLite for convenience; production deployments should use an appropriately secured database.
- External AI services, if enabled, require separately configured API credentials.
- Production deployment requires HTTPS and appropriate server/security configuration.
---

## 18. Conclusion
NSS Connect provides a centralized digital platform for managing NSS and volunteer activities. By combining event management, NGO/NSS verification, QR attendance, ABP hour tracking, feedback, certificates, maps, reporting, notifications, and rule-based recommendations, the project demonstrates how a full-stack application can streamline community-service administration.
---

## 19. Repository Security Notice
This repository is intended for academic/project demonstration and development.
Sensitive configuration is intentionally excluded from the repository. Before deploying the application publicly:
- Use strong production secrets.
- Configure HTTPS.
- Use a production database.
- Configure allowed hosts and CORS correctly.
- Configure secure cookies.
- Protect uploaded files.
- Review privacy/legal requirements.
- Do not use demo credentials in production.
- Review all environment variables before deployment.
---

## 20. License
This project is intended for academic and educational use.
See `LICENSE` for the repository license terms.
