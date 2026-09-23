# Automation Orchestrator

A portfolio prototype for config-driven business automation. The project explores how lead handling, workflow execution, CRM connectors, email actions, audit evidence and operational monitoring can be brought behind one API and dashboard.

This repository demonstrates system design and implementation work. It is not presented as a production-ready SaaS product.

## What is implemented

- a FastAPI application factory with endpoints for leads, workflows, campaigns, analytics and administration
- Salesforce and HubSpot connector modules
- workflow execution, deduplication and email-follow-up components
- JWT/API-key support, role-based access control and tenant abstractions
- audit logging, monitoring and health-check utilities
- a React/Vite dashboard
- Docker, Compose and Kubernetes deployment examples
- automated validation and security-analysis workflows

Several integrations require external credentials and remain configuration-dependent. The repository also contains demonstration data and prototype pathways that should be reviewed before any real deployment.

## Architecture

```text
React dashboard
      |
FastAPI application
      |
+-----+----------+-----------+-----------+
|                |           |           |
Workflows     CRM adapters  Email     Audit/metrics
|                |           |           |
Configuration  Salesforce  SMTP/API   Logs/reports
               HubSpot
```

## Technology

- Python 3.12, FastAPI, Pydantic and Uvicorn
- React 18, TypeScript, Vite and Tailwind CSS
- Redis-compatible queue abstraction
- Docker/Compose, Nginx, Prometheus and Kubernetes examples
- Pytest and GitHub Actions

## Local setup

Create an isolated Python environment, then install the pinned application requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Review `.env` and `config/sample_config.json` before starting the API:

```powershell
$env:PYTHONPATH = "src"
python -m automation_orchestrator.main --api --host 127.0.0.1 --port 8000
```

For the dashboard:

```powershell
Set-Location frontend
npm ci
npm run dev
```

## Validation

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -v
python security_validation.py
```

The repository includes GitHub Actions definitions for API tests, frontend builds, dependency review and static security analysis. Some checks are advisory while the prototype is being consolidated.

## Security note

No local `.env` file, generated security key, backup archive, runtime data or test-result export should be committed. Values previously exposed in Git history must be treated as compromised and replaced before use.

## Project status

Active portfolio consolidation. The current focus is reducing prototype duplication, improving reproducibility and separating demonstrator behavior from deployable components.

## Licence

Copyright John Martin. No licence is granted for reuse unless a licence file is added to this repository.
