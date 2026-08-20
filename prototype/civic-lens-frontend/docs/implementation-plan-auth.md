# Phase 8F Implementation Plan: Authentication & Role-Based Navigation Architecture (Revised)

---

## User Review Required

> [!IMPORTANT]
> **REVISED APPROVED PRODUCT REQUIREMENTS & SECURITY BOUNDARIES**
>
> 1. **Database as Single Source of Truth**: User roles (`CITIZEN`, `OPERATOR`, `SUPERVISOR`, `ADMIN`) are stored strictly in the backend SQLite `users` table. Frontend roles are NEVER trusted for authorization.
> 2. **Complete Navbar Role Switcher Removal**: The frontend role selector buttons (`Citizen | Operator | Supervisor | Admin | Public`) are completely removed from the navbar.
> 3. **Public Access Isolation**: "Public" is strictly an unauthenticated access mode. Public transparency, overview, hotspots, and participatory budget pages remain accessible without login.
> 4. **Strict HTTP 403 Forbidden Enforcement**: Authenticated users attempting unauthorized operations will receive `HTTP 403 Forbidden` from FastAPI backend dependencies.
> 5. **HTTP-Only Secure Cookie Session Strategy**: Access tokens will be stored in `HttpOnly`, `SameSite=Lax` cookies set by the backend, with `Authorization: Bearer <token>` supported for API/test clients.
> 6. **Deprecation of Legacy Key Fallback**: The legacy `X-Admin-API-Key` header will no longer act as an admin authorization bypass for user accounts.
> 7. **Explicit Ownership Verification**: Citizen access to private/mutable resources (e.g. reopening issues) will enforce resource ownership checks (`resource.created_by == current_user.id`).
> 8. **Zero Demo Credentials / Hardcoding**: No hardcoded passwords or default production credentials in codebase or Git. Safe development/testing registration flows will be used.
> 9. **Zero Breaking Changes**: All Phase 8A–8E business logic, SQLite schema tables, SLA policies, RAG vector retrieval, and geocoding features remain intact.

---

## A. Updated Architecture

```
                               ┌───────────────────────────┐
                               │   Browser / React Client  │
                               └─────────────┬─────────────┘
                                             │
                       HTTP-Only Cookie / Bearer JWT Header
                                             │
                                             ▼
                       ┌───────────────────────────────────┐
                       │       FastAPI Security Middleware │
                       │    (get_current_user Dependency) │
                       └─────────────┬─────────────────────┘
                                     │
                     Decodes & Verifies JWT Signature
                                     │
                                     ▼
                       ┌───────────────────────────────────┐
                       │     SQLite 'users' Table Query     │
                       │    (Backend Source of Truth)      │
                       └─────────────┬─────────────────────┘
                                     │
                  Checks user.is_active & user.role
                                     │
            ┌────────────────────────┴────────────────────────┐
            ▼                                                 ▼
┌───────────────────────┐                         ┌───────────────────────┐
│   Role Allowed?       │                         │   Role Unauthorized?  │
│  (Role / Ownership)   │                         │                       │
└───────────┬───────────┘                         └───────────┬───────────┘
            │                                                 │
            ▼                                                 ▼
┌───────────────────────┐                         ┌───────────────────────┐
│ Execute Endpoint Logic│                         │ HTTP 403 Forbidden    │
└───────────────────────┘                         └───────────────────────┘
```

---

## B. Authentication & Session Strategy

- **Cookie Feasibility Evaluation**:
  - **Verdict**: **Feasible & Preferred**. Since the Vite dev server proxies `/api` requests to `http://localhost:8000`, the frontend and backend share the same origin context (`localhost:5173`).
  - **Mechanics**: Upon login (`POST /api/v1/auth/login`), FastAPI responds with a `Set-Cookie` header (`access_token=...; HttpOnly; SameSite=Lax; Path=/`).
  - **Header Dual-Support**: The backend dependency `get_current_user` checks the `HttpOnly` cookie first, and falls back to checking the `Authorization: Bearer <token>` header (allowing automated `pytest` and API client testing).
  - **Logout**: `POST /api/v1/auth/logout` instructs the browser to delete the cookie via `Set-Cookie: access_token=; Max-Age=0`.

---

## C. Role & Permission Matrix

| Role | Role-Specific Permissions & Capabilities | Explicit Restrictions (Forbidden -> HTTP 403) |
| :--- | :--- | :--- |
| **PUBLIC** | View public analytics, transparency reports, hotspot project lists, participatory proposals. | Cannot submit issues, cannot vote, cannot access operational queues or admin panels. |
| **CITIZEN** | Report issues, view personal reported issues, submit proposals, cast budget votes, reopen owned issues. | Cannot access Operator triage, Supervisor queue, Admin governance, SLA policies, or RAG ingestion. |
| **OPERATOR** | View master issue triage queue, acknowledge routing, assign field work, start work, submit completion evidence. | Cannot verify supervisor evidence, cannot modify SLA/reopen policies, cannot ingest RAG docs. |
| **SUPERVISOR** | View verification queue, review evidence uploads, approve/reject resolution evidence, update reopen policies. | Cannot modify SLA policies, cannot ingest RAG docs, cannot delete master issues. |
| **ADMIN** | Manage SLA policies, configure reopen policies, ingest/manage RAG knowledge base documents, manage budget allocations. | Actions are audited; admin privileges do not bypass explicit resource ownership rules unless authorized. |

*Note: Roles do NOT automatically inherit permissions unless explicitly specified in the endpoint dependency (e.g. `require_role(["OPERATOR", "ADMIN"])`).*

---

## D. Resource Ownership Strategy

Beyond checking `user.role`, endpoints modifying specific resources will enforce ownership:

1. **Citizen Reopen Issue (`POST /api/v1/issues/{issue_id}/reopen`)**:
   - Dependency checks `master_issue.reporter_id == current_user.id` or `current_user.role in ["SUPERVISOR", "ADMIN"]`.
   - If a citizen attempts to reopen another citizen's issue $\rightarrow$ returns `HTTP 403 Forbidden`.
2. **Citizen Proposal Update / Delete (`PUT /api/v1/proposals/{proposal_id}`)**:
   - Checks `proposal.proposer_id == current_user.id`.
3. **Operator Work Claim / Start (`POST /api/v1/work/{issue_id}/start`)**:
   - Checks `assignment.operator_id == current_user.id` or `current_user.role in ["SUPERVISOR", "ADMIN"]`.

---

## E. Identity String Mapping Replacement

The following legacy identity parameters will be replaced by the backend authenticated `current_user.id`:

| Legacy Endpoint | Legacy Input Field | Replacement Mechanism |
| :--- | :--- | :--- |
| `POST /api/v1/work/assign` | `operator_id`, `assigned_by` | `assigned_by = current_user.id`; `operator_id` validated against `users` table |
| `POST /api/v1/work/{id}/start` | Hardcoded `operator_1` | Replaced by `current_user.id` (verifies user is `OPERATOR`) |
| `POST /api/v1/work/{id}/submit-completion` | Hardcoded `operator_1` | Replaced by `current_user.id` |
| `POST /api/v1/evidence/upload` | `uploader_id` | Replaced by `current_user.id` |
| `POST /api/v1/evidence/{id}/verify` | `supervisor_id` | Replaced by `current_user.id` (verifies user is `SUPERVISOR`) |
| `POST /api/v1/proposals` | `proposer_id_hash` | Derived from `hash(current_user.id)` |
| `POST /api/v1/admin/rag/ingest` | `user_id` | Replaced by `current_user.id` (verifies user is `ADMIN`) |

---

## F. Endpoint Access Classification

### 1. Public Read-Only Endpoints (No Auth Required)
- `GET /health/db`
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/hotspots`
- `GET /api/v1/project-opportunities`
- `GET /api/v1/public/issues/{anonymized_id}`
- `GET /api/v1/public/issues/{anonymized_id}/timeline`
- `GET /api/v1/public/evidence/{public_token}`
- `GET /api/v1/finance/cycles`
- `GET /api/v1/finance/proposals`

### 2. Protected Endpoints Requiring Token & Role Verification
- **Auth Routes**: `POST /api/v1/auth/register` (Public), `POST /api/v1/auth/login` (Public), `POST /api/v1/auth/logout` (Authenticated), `GET /api/v1/auth/me` (Authenticated).
- **Citizen (`CITIZEN`)**: `POST /api/v1/ai/extract-location`, `POST /api/v1/ai/analyze-complaint`, `POST /api/v1/ai/analyze-audio`, `POST /api/v1/ai/analyze-image`, `POST /api/v1/ai/duplicates/check`, `POST /api/v1/stt/transcribe`, `POST /api/v1/vision/analyze`, `POST /api/v1/issues/{id}/reopen` (with ownership check), `POST /api/v1/proposals`, `POST /api/v1/voting/vote`.
- **Operator (`OPERATOR`)**: `GET /api/v1/ai/master-issues`, `POST /api/v1/priority/calculate`, `POST /api/v1/routing/route`, `POST /api/v1/routing/{id}/acknowledge`, `POST /api/v1/work/assign`, `POST /api/v1/work/{id}/start`, `POST /api/v1/work/{id}/submit-completion`, `POST /api/v1/evidence/upload`.
- **Supervisor (`SUPERVISOR`)**: `GET /api/v1/supervisor/verification-queue`, `POST /api/v1/evidence/{id}/verify`, `GET /api/v1/admin/reopen-policies`, `POST /api/v1/admin/reopen-policies`, `PUT /api/v1/admin/reopen-policies/{id}`.
- **Admin (`ADMIN`)**: `GET /api/v1/admin/sla-policies`, `POST /api/v1/admin/sla-policies`, `PUT /api/v1/admin/sla-policies/{id}`, `DELETE /api/v1/admin/sla-policies/{id}`, `POST /api/v1/admin/rag/ingest`, `GET /api/v1/admin/rag/documents`, `POST /api/v1/finance/cycles`, `POST /api/v1/finance/estimates`, `POST /api/v1/finance/cycles/{id}/allocate`.

---

## G. Database Changes

Additive SQLite table `users` in `app/database/models.py`:

```python
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="CITIZEN", index=True) # CITIZEN, OPERATOR, SUPERVISOR, ADMIN
    jurisdiction_id = Column(String(64), nullable=False, default="GLOBAL")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
```

---

## H. Frontend Changes

1. **Navbar Removal**: Remove the role switcher button strip from `Navbar.tsx`.
2. **Auth Context**: Update `AuthContext.tsx` to read user status from `/api/v1/auth/me` via HTTP-only cookie.
3. **Route Protection**: Wrap Citizen, Operator, Supervisor, and Admin routes in `<ProtectedRoute allowedRoles={[...]}>`.
4. **Auth Pages**: Provide clean `/login` and `/register` pages.

---

## I. Security Considerations

1. **CSRF Protection for Cookies**: `SameSite=Lax` cookie setting prevents cross-site request forgery in modern browsers.
2. **Credential Storage**: Passwords hashed using PBKDF2-HMAC-SHA256 with 100,000 iterations and per-user 16-byte random salts.
3. **Deprecation of Key Bypass**: Administrative routes strictly require a valid JWT token with `ADMIN` role.
4. **Inactive User Check**: Inactive accounts (`is_active == False`) are immediately rejected by `login` and `get_current_user`.

---

## J. Test Plan (Mandatory Coverage)

The test suite in `tests/test_auth.py` will explicitly test and assert:

1. `test_user_registration`: User self-registration returns `HTTP 201 Created`.
2. `test_duplicate_email_registration`: Registering an existing email returns `HTTP 400 Bad Request`.
3. `test_valid_login`: Correct email/password returns JWT token and sets `access_token` cookie.
4. `test_invalid_password`: Incorrect password returns `HTTP 401 Unauthorized`.
5. `test_invalid_or_expired_token`: Malformed or expired JWT token returns `HTTP 401 Unauthorized`.
6. `test_auth_me`: `/api/v1/auth/me` returns current user profile for valid cookie/token.
7. `test_unauthenticated_protected_route`: Accessing `/api/v1/admin/sla-policies` without auth returns `HTTP 401`.
8. `test_citizen_cannot_access_admin_api`: Citizen token accessing `/api/v1/admin/sla-policies` returns `HTTP 403 Forbidden`.
9. `test_operator_cannot_access_admin_api`: Operator token accessing `/api/v1/admin/sla-policies` returns `HTTP 403 Forbidden`.
10. `test_supervisor_cannot_access_admin_api`: Supervisor token accessing `/api/v1/admin/sla-policies` returns `HTTP 403 Forbidden`.
11. `test_authorized_admin_accesses_admin_api`: Admin token accessing `/api/v1/admin/sla-policies` succeeds with `HTTP 200 OK`.
12. `test_citizen_resource_ownership`: Citizen A attempting to reopen Citizen B's issue returns `HTTP 403 Forbidden`.
13. `test_public_endpoint_without_authentication`: `/api/v1/analytics/summary` is accessible without cookie/header (`HTTP 200 OK`).
14. `test_inactive_user_cannot_authenticate`: User with `is_active=False` is denied login (`HTTP 403 Forbidden`).
