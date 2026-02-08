<<<<<<< HEAD
# Dockerfile for Automation Orchestrator API
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/automation_orchestrator/main.py ./main.py

EXPOSE 8000

CMD ["python", "main.py"]
=======
# Production Dockerfile for Automation Orchestrator
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.12-slim as builder

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
RUN mkdir -p /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Command to run
CMD ["python", "-m", "automation_orchestrator.main", "--api", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
