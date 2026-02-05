import json
import os
import sys
import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)


def setup_logging(log_path: str, log_level: str = "INFO", name: str = "AutomationOrchestrator") -> None:
    """Setup logging configuration"""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )


def run(config_path: str, api_mode: bool = False, api_host: str = "0.0.0.0", 
        api_port: int = 8000) -> None:
    """
    Run Automation Orchestrator
    
    Args:
        config_path: Path to configuration file
        api_mode: If True, run REST API server instead of CLI
        api_host: API server host
        api_port: API server port
    """
    cfg = load_config(config_path)
    log_path = cfg.get("log_path", "./logs/automation_orchestrator.log")
    setup_logging(log_path, log_level=cfg.get("log_level", "INFO"), 
                  name="Automation Orchestrator")
    
    print("Automation Orchestrator started with config:")
    print(json.dumps(cfg, indent=2))
    
    if api_mode:
        run_api(cfg, host=api_host, port=api_port)
    else:
        run_cli(cfg)


def run_cli(config: dict) -> None:
    """Run Automation Orchestrator in CLI mode"""
    try:
        from automation_orchestrator.lead_ingest import LeadIngest
        from automation_orchestrator.crm_connector import GenericAPIConnector
        from automation_orchestrator.workflow_runner import WorkflowRunner
        from automation_orchestrator.email_followup import EmailFollowup
        
        lead_ingest = LeadIngest(config.get('lead_ingest', {}))
        crm_connector = GenericAPIConnector(config.get('crm', {}))
        email_followup = EmailFollowup(config.get('email', {}))
        workflow_runner = WorkflowRunner(
            config.get('workflow', {}),
            lead_ingest,
            crm_connector,
            email_followup
        )
        
        # Start workflow runner
        workflow_runner.start()
        
        print("✓ Automation Orchestrator running in CLI mode")
        print("  Press Ctrl+C to stop...")
        
        # Keep running
        import time
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n✓ Automation Orchestrator stopped")
    except Exception as e:
        logger.error(f"Error running CLI mode: {e}", exc_info=True)
        raise


def run_api(config: dict, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run Automation Orchestrator as REST API server"""
    try:
        import uvicorn
        from automation_orchestrator.api import create_app
        from automation_orchestrator.lead_ingest import LeadIngest
        from automation_orchestrator.crm_connector import GenericAPIConnector
        from automation_orchestrator.workflow_runner import WorkflowRunner
        from automation_orchestrator.email_followup import EmailFollowup
        
        # Initialize modules
        lead_ingest = LeadIngest(config.get('lead_ingest', {}))
        crm_connector = GenericAPIConnector(config.get('crm', {}))
        email_followup = EmailFollowup(config.get('email', {}))
        workflow_runner = WorkflowRunner(
            config.get('workflow', {}),
            lead_ingest,
            crm_connector,
            email_followup
        )
        
        # Create API app
        app = create_app(
            config,
            lead_ingest=lead_ingest,
            crm_connector=crm_connector,
            workflow_runner=workflow_runner,
            email_followup=email_followup
        )
        
        print(f"\n✓ Starting REST API Server")
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  Documentation: http://{host}:{port}/api/docs")
        print(f"  OpenAPI Schema: http://{host}:{port}/api/openapi.json")
        
        # Run server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    
    except ImportError as e:
        logger.error(f"Missing required packages for API mode: {e}")
        print("✗ Failed to start API mode. Install requirements:")
        print("  pip install -r requirements.txt")
        raise
    except Exception as e:
        logger.error(f"Error running API mode: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automation Orchestrator - Config-driven automation platform"
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("AO_CONFIG", "./config/sample_config.json"),
        help="Path to configuration file"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Run in REST API mode instead of CLI mode"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    
    args = parser.parse_args()
    
    run(args.config, api_mode=args.api, api_host=args.host, api_port=args.port)
