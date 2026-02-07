# Dockerfile for Automation Orchestrator API
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/automation_orchestrator/main.py ./main.py

EXPOSE 8000

CMD ["python", "main.py"]
