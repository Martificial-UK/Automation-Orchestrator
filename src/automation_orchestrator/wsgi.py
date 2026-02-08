"""
Gunicorn + Uvicorn production-ready deployment
Run with: gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.automation_orchestrator.wsgi:app
"""

import json
import os
import logging
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from automation_orchestrator.api import create_app
from automation_orchestrator.lead_ingest import LeadIngest
from automation_orchestrator.crm_connector import GenericAPIConnector
from automation_orchestrator.workflow_runner import WorkflowRunner
from automation_orchestrator.email_followup import EmailFollowup

logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> dict:
    """Load configuration from JSON file"""
    if config_path is None:
        config_path = os.environ.get("AO_CONFIG", "./config/sample_config.json")
    
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)


# Load config at module level for Gunicorn
cfg = load_config()

# Initialize modules
lead_ingest = LeadIngest(cfg.get('lead_ingest', {}))
crm_connector = GenericAPIConnector(cfg.get('crm', {}))
email_followup = EmailFollowup(cfg.get('email', {}))
workflow_runner = WorkflowRunner(
    cfg.get('workflow', {}),
    lead_ingest,
    crm_connector,
    email_followup
)

# Create FastAPI app
app = create_app(
    cfg,
    lead_ingest=lead_ingest,
    crm_connector=crm_connector,
    workflow_runner=workflow_runner,
    email_followup=email_followup
)

if __name__ == "__main__":
    # Local development
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
