---
name: ciberseguridad-senior
description: Use when reviewing security posture, implementing auth/authorization, hardening APIs, addressing OWASP Top 10, configuring CORS, rate limiting, session management, secrets handling, audit logging, or performing threat modeling. Includes NIST SP 800-228 API protection guidelines and OWASP API Security Top 10 (2023).
---

# Senior Cybersecurity Engineer

## Standards Referenced
- **OWASP API Security Top 10** (2023 edition — current authoritative reference)
- **NIST SP 800-228**: Guidelines for API Protection for Cloud-Native Systems (June 2025)
- **OWASP Top 10 Web**: Traditional web app risks

## OWASP API Security Top 10 — Full Mitigation Matrix

| # | Risk | This Project Mitigation | Verification |
|---|---|---|---|
| API1 | **Broken Object Level Authorization (BOLA)** | Ownership checks in every route; never trust user-supplied IDs without verifying | Code review each route |
| API2 | **Broken Authentication** | Session-based httpOnly cookies; bcrypt hashing; `verify_password()` on every login | Pen test login flow |
| API3 | **Broken Object Property Level (Mass Assignment)** | Pydantic response models whitelist fields; never return raw MongoDB docs | Schema audit |
| API4 | **Unrestricted Resource Consumption** | Rate limiting via Redis token bucket; pagination on all list endpoints | Load test |
| API5 | **Broken Function Level Authorization** | `require_permission("permission_code")` decorator on every management route | Auth test per role |
| API6 | **Unrestricted Access to Sensitive Business Flows** | Rate limiting + human detection on login; audit log on sensitive actions | Business flow review |
| API7 | **Server-Side Request Forgery (SSRF)** | Validate and restrict outbound URLs; block private IP ranges | URL validation audit |
| API8 | **Security Misconfiguration** | CORS allowlist; debug disabled in production; headers configured | Config review |
| API9 | **Improper Inventory Management** | Route registry in `main.py`; no orphan endpoints; versioned APIs | Route audit |
| API10 | **Unsafe Consumption of APIs** | Validate all third-party API responses; sanitize inputs | Dependency audit |

## Critical Controls

### 1. Authentication (Current Implementation ✅)
```python
# Session-based auth
SESSION_COOKIE_NAME = "hoteldata_session"
# httpOnly=True, samesite="lax", max_age=8h
# Server-side session invalidation on logout
# Rate-limited login (5 attempts/min per IP via Redis)
```

**Never**: JWT in localStorage, API keys in URL params, tokens in client-side code

### 2. Authorization (Current Implementation ✅)
```
9 roles: super_admin → cliente
11 permissions: dashboard.read, users.manage, etl.execute, etc.
Route-level: require_permission("permission_code")
Middleware: role_access_middleware (global enforcement)
```

### 3. CORS (Current Config)
```python
allow_origins = ["http://127.0.0.1:4200", "http://localhost:4200", "http://localhost"]
```
**Production rule**: Only the actual domain. Never `["*"]`.

### 4. Rate Limiting (Redis Token Bucket)
```python
# Apply to:
POST /api/auth/login         → 5/min per IP
POST /api/auth/register      → 3/h per IP
POST /etl-status/seed        → 1/h per user
POST/PUT/DELETE endpoints    → 100/min per user
```

### 5. Security Headers (nginx)
```
# /etc/nginx/conf.d/security.conf
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

### 6. Audit Trail
```python
# Every auth event logged to user_activity_logs:
- action: "auth.login_failed" / "auth.login_success" / "auth.logout"
- ip_address, user_agent, timestamp
- admin actions: role changes, user toggle, ETL seeds
```

### 7. Secret Management
```yaml
# Never in code:
- .env file (gitignored)
- Docker secrets for production
- POCKETBASE_ADMIN_PASSWORD rotated regularly
- No secrets in logs (filter in logger config)

# Current .env (example — never commit real values)
POCKETBASE_ADMIN_EMAIL=
POCKETBASE_ADMIN_PASSWORD=
```

### 8. Input Validation
- **All inputs**: Validated by Pydantic v2 before reaching business logic
- **MongoDB**: Parameterized queries only — no string interpolation
- **Files**: Validate MIME type, size limit (future: ClamAV scan)

### 9. Session Security
```
- httpOnly: true    (JS cannot read the cookie)
- samesite: lax     (CSRF protection)
- max_age: 8h       (forced re-login)
- path: /           (available across app)
- secure: true      (in production, over HTTPS)
- Server-side invalidation on logout
```

## Threat Model (STRIDE per Component)

| Component | Spoofing | Tampering | Repudiation | Info Disclosure | DoS | Elevation |
|---|---|---|---|---|---|---|
| Nginx | TLS cert | — | — | Headers | Rate limit | — |
| FastAPI | Auth check | Input validation | Audit log | Pydantic models | Rate limit | Permission check |
| MongoDB | Connection string | Write concern | Change stream | Encryption at rest | Connection pool | — |
| Redis | Password | — | — | — | Pool size limit | — |
| Angular | — | Input sanitization | — | No secrets in client | Lazy loading | Route guards |

## Secure Coding Checklist
- [ ] No secrets in code, logs, or error messages
- [ ] All user input validated by Pydantic v2
- [ ] Object ownership verified (BOLA prevention)
- [ ] Rate limiting on auth endpoints
- [ ] CORS restricted to known origins
- [ ] Session cookie: httpOnly + SameSite + Secure (prod)
- [ ] Debug/development endpoints disabled in production
- [ ] All dependencies version-pinned in `requirements.txt`
- [ ] `user_activity_logs` records every auth event
- [ ] MongoDB connection string has no hardcoded credentials
- [ ] SQL/NOSQL injection impossible (parameterized queries)
- [ ] File uploads validated (when implemented)

## Dependency Vulnerability Management
```bash
# Regular checks
docker compose exec app pip audit          # Check Python deps
npm audit                                   # Check Angular deps
docker scout cve hoteldata_project-app      # Docker image scan
```

## References
- OWASP API Security Top 10: https://owasp.org/API-Security/
- NIST SP 800-228: https://csrc.nist.gov/pubs/sp/800/228/final
- JWT Security Cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
