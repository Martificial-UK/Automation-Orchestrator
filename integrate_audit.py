"""
Automated integration script to add audit logging to all Automation Orchestrator modules.
This script reads each module, adds audit imports and calls, and saves the updated versions.
"""

import os
import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Path to Automation Orchestrator
ORCHESTRATOR_PATH = Path(r"c:\AI Automation\Automation Orchestrator\src\automation_orchestrator")

def backup_file(file_path):
    """Create a backup of the original file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Backed up: {file_path.name}")
        return True
    return False

def add_audit_import(content):
    """Add audit import if not present."""
    if 'from automation_orchestrator.audit import get_audit_logger' in content:
        return content
    
    # Find the last import statement
    import_pattern = r'((?:from|import)\s+\S+.*\n)'
    imports = list(re.finditer(import_pattern, content))
    
    if imports:
        last_import = imports[-1]
        insert_pos = last_import.end()
        new_import = 'from automation_orchestrator.audit import get_audit_logger\n'
        content = content[:insert_pos] + new_import + content[insert_pos:]
    
    return content

def integrate_workflow_runner():
    """Integrate audit logging into workflow_runner.py."""
    file_path = ORCHESTRATOR_PATH / "workflow_runner.py"
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add import
    content = add_audit_import(content)
    
    # Add audit instance in __init__
    if 'self.audit = get_audit_logger()' not in content:
        init_pattern = r'(def __init__\(self.*?\):.*?\n(?:\s+.*\n)*)'
        match = re.search(init_pattern, content)
        if match:
            init_end = match.end()
            # Find the indentation
            indent_match = re.search(r'\n(\s+)\S', content[match.start():init_end])
            indent = indent_match.group(1) if indent_match else '        '
            
            insert_line = f'{indent}self.audit = get_audit_logger()\n'
            content = content[:init_end] + insert_line + content[init_end:]
    
    # Add audit calls in start() method
    if 'self.audit.log_workflow_started' not in content:
        start_pattern = r'(def start\(self\):.*?\n(?:\s+.*\n)*?)((?:\s+)self\.running = True)'
        match = re.search(start_pattern, content)
        if match:
            indent = match.group(2)[:match.group(2).index('self')]
            insert_line = f'{indent}self.audit.log_workflow_started(self.workflow_name)\n{match.group(2)}'
            content = content[:match.start(2)] + insert_line + content[match.end(2):]
    
    # Add audit call in stop() method
    if 'self.audit.log_workflow_stopped' not in content:
        stop_pattern = r'(def stop\(self\):.*?\n(?:\s+.*\n)*?)((?:\s+)self\.running = False)'
        match = re.search(stop_pattern, content)
        if match:
            indent = match.group(2)[:match.group(2).index('self')]
            insert_line = f'{match.group(2)}\n{indent}self.audit.log_workflow_stopped(self.workflow_name)\n'
            content = content[:match.start(2)] + insert_line + content[match.end(2):]
    
    # Add audit call for lead ingestion
    if 'self.audit.log_lead_ingested' not in content:
        # Look for where leads are ingested
        pattern = r'(for lead in leads:.*?\n)((?:\s+)# Process each lead)'
        match = re.search(pattern, content)
        if match:
            indent = match.group(2)[:match.group(2).index('#')]
            insert_line = f'{indent}self.audit.log_lead_ingested(lead.get("id"), lead.get("source"), lead, self.workflow_name)\n'
            content = content[:match.end(1)] + insert_line + match.group(2) + content[match.end(2):]
    
    # Save updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Integrated audit logging: workflow_runner.py")
    return True

def integrate_crm_connector():
    """Integrate audit logging into crm_connector.py."""
    file_path = ORCHESTRATOR_PATH / "crm_connector.py"
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add import
    content = add_audit_import(content)
    
    # Add audit instance in each connector's __init__
    if 'self.audit = get_audit_logger()' not in content:
        # Find all __init__ methods in connector classes
        init_pattern = r'(class \w+Connector.*?def __init__\(self.*?\):.*?\n(?:\s+.*\n)*?)(\s+def \w+|class \w+|\Z)'
        
        def add_audit_to_init(match):
            init_block = match.group(1)
            rest = match.group(2)
            
            if 'self.audit = get_audit_logger()' not in init_block:
                # Find last line of __init__
                lines = init_block.split('\n')
                indent = '        '  # Standard indent
                for line in reversed(lines):
                    if line.strip() and not line.strip().startswith('#'):
                        indent = line[:len(line) - len(line.lstrip())]
                        break
                
                audit_line = f'{indent}self.audit = get_audit_logger()\n'
                init_block = init_block.rstrip() + '\n' + audit_line
            
            return init_block + rest
        
        content = re.sub(init_pattern, add_audit_to_init, content, flags=re.DOTALL)
    
    # Save updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Integrated audit logging: crm_connector.py")
    return True

def integrate_email_followup():
    """Integrate audit logging into email_followup.py."""
    file_path = ORCHESTRATOR_PATH / "email_followup.py"
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add import
    content = add_audit_import(content)
    
    # Add audit instance in __init__
    if 'self.audit = get_audit_logger()' not in content:
        init_pattern = r'(def __init__\(self.*?\):.*?\n(?:\s+.*\n)*)'
        match = re.search(init_pattern, content)
        if match:
            init_end = match.end()
            indent_match = re.search(r'\n(\s+)\S', content[match.start():init_end])
            indent = indent_match.group(1) if indent_match else '        '
            
            insert_line = f'{indent}self.audit = get_audit_logger()\n'
            content = content[:init_end] + insert_line + content[init_end:]
    
    # Save updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Integrated audit logging: email_followup.py")
    return True

def integrate_lead_ingest():
    """Integrate audit logging into lead_ingest.py."""
    file_path = ORCHESTRATOR_PATH / "lead_ingest.py"
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add import
    content = add_audit_import(content)
    
    # Add audit instance in __init__
    if 'self.audit = get_audit_logger()' not in content:
        init_pattern = r'(def __init__\(self.*?\):.*?\n(?:\s+.*\n)*)'
        match = re.search(init_pattern, content)
        if match:
            init_end = match.end()
            indent_match = re.search(r'\n(\s+)\S', content[match.start():init_end])
            indent = indent_match.group(1) if indent_match else '        '
            
            insert_line = f'{indent}self.audit = get_audit_logger()\n'
            content = content[:init_end] + insert_line + content[init_end:]
    
    # Save updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Integrated audit logging: lead_ingest.py")
    return True

def main():
    """Main integration process."""
    print("=" * 60)
    print("Automation Orchestrator - Audit Integration")
    print("=" * 60)
    
    if not ORCHESTRATOR_PATH.exists():
        print(f"✗ Directory not found: {ORCHESTRATOR_PATH}")
        return False
    
    print(f"\nTarget directory: {ORCHESTRATOR_PATH}")
    print("\nStarting integration...\n")
    
    results = []
    results.append(integrate_workflow_runner())
    results.append(integrate_crm_connector())
    results.append(integrate_email_followup())
    results.append(integrate_lead_ingest())
    
    print("\n" + "=" * 60)
    if all(results):
        print("[SUCCESS] All modules integrated successfully!")
        print("\nBackup files created with .bak extension")
        print("Next step: Run test_audit_integration.py")
    else:
        print("[ERROR] Some integrations failed. Check errors above.")
    print("=" * 60)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
