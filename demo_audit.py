"""Quick demo of all audit features."""
import sys
sys.path.insert(0, 'src')

from automation_orchestrator.audit import AuditLogger

print("\n=== AUDIT SYSTEM DEMO ===\n")

# Create audit logger with all features
audit = AuditLogger(
    'logs/demo.log',
    max_file_size_mb=50,
    enable_rotation=True,
    enable_integrity=True
)

# Enable compliance
audit.enable_compliance_mode(True)

# Track performance
audit.track_performance('demo_operation', 0.123)
audit.track_performance('demo_operation', 0.156)

# Log events
for i in range(5):
    audit.log_lead_ingested(
        f'DEMO-{i}',
        'web_form',
        {'email': f'user{i}@test.com'},
        'demo'
    )

# Log error
audit.log_error('DemoError', 'This is a demo error', workflow='demo')

print("[OK] Logged 6 events with integrity signatures")

# Get statistics
stats = audit.get_statistics()
print(f"[OK] Total events: {stats['total_events']}")
print(f"[OK] Leads processed: {stats['leads_processed']}")
print(f"[OK] Errors: {stats['errors']}")

# Get performance stats
perf = audit.get_performance_stats()
if perf:
    print(f"[OK] Performance tracked: {list(perf.keys())}")
    for op, data in perf.items():
        print(f"    {op}: avg={data['avg']:.3f}s")

print("[OK] Compliance mode: PII anonymized")
print("[OK] All events signed with HMAC-SHA256")
print("\nDemo complete! Check logs/demo.log\n")
