# Deployment Checklist (Production)

Use this checklist for production releases of Automation Orchestrator.

## 1) Pre-Release Readiness
Release details:
- Version/tag: v1.0.1 (pre-release)
- Scope: DevOps hardening
- Changelog summary: CI/CD hardening, caching, audits, frontend build/lint, release automation
- Data migration: None

- [x] Confirm release scope, version tag, and changelog summary
- [x] Ensure CI is green on `main` (ci-cd + ao-validation)
- [x] Verify dependency audit reports are reviewed
- [x] Confirm no uncommitted changes or local-only configs
- [x] Confirm customer data migration plan (if applicable)

## 2) Security & Compliance
Status notes:
- Secrets storage: Not decided yet
- `JWT_SECRET` / `LICENSE_SECRET`: Not set to non-default values yet
- TLS certificates: Not set yet
- Audit logging & PII handling: Not verified yet

- [ ] Secrets are stored in a manager (not in repo or .env)
- [ ] `JWT_SECRET` and `LICENSE_SECRET` are non-default
- [ ] TLS certificates are valid and rotated
- [ ] Audit logging enabled and tested
- [ ] PII handling reviewed (retention + anonymization settings)

## 3) Infrastructure & Config
Status notes:
- Production config file: Not validated yet
- Environment variables: Not validated yet
- Database/Redis connectivity: Not verified yet
- DNS / reverse proxy: Not validated yet
- Firewall rules/ports: Not validated yet

- [ ] Production config file validated
- [ ] Environment variables validated
- [ ] Database connectivity and backups verified
- [ ] Redis connectivity verified
- [ ] DNS / reverse proxy configuration verified
- [ ] Firewall rules and ports validated

## 4) Build & Release
Status notes:
- Version tag: Not created yet
- Docker image: Not built/published yet
- GitHub release: Not created yet
- Frontend build artifact: Not verified yet

- [ ] Create version tag `vX.Y.Z`
- [ ] CI builds Docker image and publishes to registry
- [ ] GitHub release created with notes
- [ ] Frontend build artifact verified

## 5) Deploy
Status notes:
- Deployment: Not deployed yet
- Config updates: Not applied yet
- Migrations: Required, not run
- Health verification: Not verified yet

- [ ] Pull new image to production host
- [ ] Apply configuration updates
- [ ] Run database migrations (if required)
- [ ] Start services and verify health endpoints
- [ ] Confirm UI loads at `/` and API docs at `/api/docs`

## 6) Post-Deploy Validation
Status notes:
- Smoke test: Not run yet
- Metrics/alerts: Not verified yet
- Logs: Not checked yet
- License status: Not confirmed yet

- [ ] Smoke test: login, lead create, workflow trigger
- [ ] Verify metrics endpoint and alerts
- [ ] Check logs for errors/warnings
- [ ] Confirm license status and activation

## 7) Rollback Plan
- [ ] Identify previous stable version and image tag
- [ ] Confirm rollback steps documented and accessible
- [ ] Test rollback on staging (if available)

## 8) Sign-Off
- [ ] Engineering sign-off
- [ ] Security sign-off
- [ ] Product/Operations sign-off

---

Notes:
- Keep secrets out of git.
- Attach incident runbook and on-call contacts for launch windows.
