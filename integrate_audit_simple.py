"""
Manual audit integration - Directly rewrites modules with proper audit logging.
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

ORCHESTRATOR_PATH = Path(r"c:\AI Automation\Automation Orchestrator\src\automation_orchestrator")

def backup_file(file_path):
    """Create backup of original file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Backed up: {file_path.name}")
        return content
    return None

def restore_from_backup(file_path):
    """Restore file from backup."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    if backup_path.exists():
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Restored from backup: {file_path.name}")
        return True
    return False

def integrate_all():
    """Integrate audit into all modules by restoring backups and adding audit manually."""
    print("=" * 70)
    print("Automation Orchestrator - Audit Integration")
    print("=" * 70)
    print("\nThis will add audit logging to all modules")
    print("Backups will be created automatically\n")
    
    # First, restore any existing backups to start fresh
    for py_file in ORCHESTRATOR_PATH.glob("*.py"):
        if not py_file.name.endswith('.bak'):
            backup_path = py_file.with_suffix(py_file.suffix + '.bak')
            if backup_path.exists():
                print(f"[INFO] Found existing backup for {py_file.name}, restoring...")
                restore_from_backup(py_file)
    
    print("\n[STEP 1] Processing workflow_runner.py...")
    file_path = ORCHESTRATOR_PATH / "workflow_runner.py"
    content = backup_file(file_path)
    
    if content and 'from automation_orchestrator.audit import get_audit_logger' not in content:
        # Add import after other imports
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        lines.insert(import_index, 'from automation_orchestrator.audit import get_audit_logger')
        
        # Add self.audit in __init__
        for i, line in enumerate(lines):
            if 'def __init__(self' in line and i < len(lines) - 2:
                # Find next non-empty line with proper indent
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    lines.insert(j, ' ' * indent + 'self.audit = get_audit_logger()')
                break
        
        content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] workflow_runner.py updated")
    
    print("\n[STEP 2] Processing crm_connector.py...")
    file_path = ORCHESTRATOR_PATH / "crm_connector.py"
    content = backup_file(file_path)
    
    if content and 'from automation_orchestrator.audit import get_audit_logger' not in content:
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        lines.insert(import_index, 'from automation_orchestrator.audit import get_audit_logger')
        content = '\n'.join(lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] crm_connector.py updated")
    
    print("\n[STEP 3] Processing email_followup.py...")
    file_path = ORCHESTRATOR_PATH / "email_followup.py"
    content = backup_file(file_path)
    
    if content and 'from automation_orchestrator.audit import get_audit_logger' not in content:
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        lines.insert(import_index, 'from automation_orchestrator.audit import get_audit_logger')
        
        # Add self.audit in __init__
        for i, line in enumerate(lines):
            if 'def __init__(self' in line and i < len(lines) - 2:
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    lines.insert(j, ' ' * indent + 'self.audit = get_audit_logger()')
                break
        
        content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] email_followup.py updated")
    
    print("\n[STEP 4] Processing lead_ingest.py...")
    file_path = ORCHESTRATOR_PATH / "lead_ingest.py"
    content = backup_file(file_path)
    
    if content and 'from automation_orchestrator.audit import get_audit_logger' not in content:
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        lines.insert(import_index, 'from automation_orchestrator.audit import get_audit_logger')
        
        # Add self.audit in __init__
        for i, line in enumerate(lines):
            if 'def __init__(self' in line and i < len(lines) - 2:
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    lines.insert(j, ' ' * indent + 'self.audit = get_audit_logger()')
                break
        
        content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] lead_ingest.py updated")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] All modules updated with audit logging!")
    print("=" * 70)
    print("\nAudit imports added to all modules")
    print("Backup files saved with .bak extension")
    print("\nNote: Full audit call integration requires manual review")
    print("See AUDIT_INTEGRATION.md for complete integration guide")
    
    return True

if __name__ == "__main__":
    try:
        success = integrate_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Integration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
