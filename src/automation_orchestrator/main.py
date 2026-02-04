import json
import os
from engine.engine import load_config, setup_logging

def run(config_path: str) -> None:
    cfg = load_config(config_path)
    log_path = cfg.get("log_path", "./logs/automation_orchestrator.log")
    setup_logging(log_path, log_level=cfg.get("log_level", "INFO"), name="Automation Orchestrator")
    print("Automation Orchestrator started with config:")
    print(json.dumps(cfg, indent=2))

if __name__ == "__main__":
    config_path = os.environ.get("AO_CONFIG", "./config/sample_config.json")
    run(config_path)
