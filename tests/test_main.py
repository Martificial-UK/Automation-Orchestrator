import os
from automation_orchestrator.main import run

def test_run(tmp_path, capsys):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"log_path": "./logs/test.log", "log_level": "INFO"}')
    run(str(cfg_path))
    captured = capsys.readouterr()
    assert "Automation Orchestrator started" in captured.out
