"""
Simple wrapper to run integration and capture output.
"""

import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

orchestrator_path = Path(r"c:\AI Automation\Automation Orchestrator")

print("=" * 70)
print("AUDIT INTEGRATION - Running...")
print("=" * 70)

# Run integration
print("\n[Step 1/2] Running integration script...")
result1 = subprocess.run(
    [sys.executable, "integrate_audit.py"],
    cwd=orchestrator_path,
    capture_output=True,
    text=True
)

print(result1.stdout)
if result1.stderr:
    print("STDERR:", result1.stderr)

if result1.returncode != 0:
    print(f"\n✗ Integration failed with exit code {result1.returncode}")
    sys.exit(1)

print("\n✓ Integration completed")

# Run tests
print("\n[Step 2/2] Running test suite...")
result2 = subprocess.run(
    [sys.executable, "test_audit_integration.py"],
    cwd=orchestrator_path,
    capture_output=True,
    text=True
)

print(result2.stdout)
if result2.stderr:
    print("STDERR:", result2.stderr)

if result2.returncode != 0:
    print(f"\n✗ Tests failed with exit code {result2.returncode}")
    sys.exit(1)

print("\n✓ All tests passed")

print("\n" + "=" * 70)
print("✓ AUDIT INTEGRATION COMPLETE")
print("=" * 70)
print("\nBackup files: *.py.bak")
print("Audit logs: logs/audit.log")
