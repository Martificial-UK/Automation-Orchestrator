# Deployment Checklist (Production)

Use this checklist for production releases of Automation Orchestrator.

## 1) Pre-Release Readiness
- [ ] Confirm release scope, version tag, and changelog summary
- [ ] Ensure CI is green on `main` (ci-cd + ao-validation)
- [ ] Verify dependency audit reports are reviewed
- [ ] Confirm no uncommitted changes or local-only configs
- [ ] Confirm customer data migration plan (if applicable)

## 2) Security & Compliance
- [ ] Secrets are stored in a manager (not in repo or .env)
- [ ] `JWT_SECRET` and `LICENSE_SECRET` are non-default
- [ ] TLS certificates are valid and rotated
- [ ] Audit logging enabled and tested
- [ ] PII handling reviewed (retention + anonymization settings)

## 3) Infrastructure & Config
- [ ] Production config file validated
- [ ] Environment variables validated
- [ ] Database connectivity and backups verified
- [ ] Redis connectivity verified
- [ ] DNS / reverse proxy configuration verified
- [ ] Firewall rules and ports validated

## 4) Build & Release
- [ ] Create version tag `vX.Y.Z`
- [ ] CI builds Docker image and publishes to registry
- [ ] GitHub release created with notes
- [ ] Frontend build artifact verified

## 5) Deploy
- [ ] Pull new image to production host
- [ ] Apply configuration updates
- [ ] Run database migrations (if required)
- [ ] Start services and verify health endpoints
- [ ] Confirm UI loads at `/` and API docs at `/api/docs`

## 6) Post-Deploy Validation
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
