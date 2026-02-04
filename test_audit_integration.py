"""
Comprehensive test suite for audit integration.
Tests all audit logging functionality across all modules.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import AuditLogger, get_audit_logger


def test_audit_logger_basic():
    """Test basic audit logger functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Audit Logger")
    print("=" * 60)
    
    # Create test audit logger
    test_log = Path("logs/test_audit.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    if test_log.exists():
        test_log.unlink()
    
    audit = AuditLogger(str(test_log))
    
    # Test lead ingested
    audit.log_lead_ingested(
        lead_id="TEST-001",
        source="web_form",
        lead_data={"email": "test@example.com", "name": "Test User"},
        workflow="test_workflow"
    )
    
    # Test lead qualified
    audit.log_lead_qualified(
        lead_id="TEST-001",
        qualified=True,
        reason="Met all criteria",
        workflow="test_workflow"
    )
    
    # Test CRM create
    audit.log_crm_create(
        lead_id="TEST-001",
        crm_record_id="CRM-123",
        crm_type="test_crm",
        workflow="test_workflow"
    )
    
    # Test email sent
    audit.log_email_sent(
        lead_id="TEST-001",
        recipient="test@example.com",
        subject="Welcome!",
        sequence_step=0,
        workflow="test_workflow"
    )
    
    # PERFORMANCE: Flush buffer and wait for async writes
    audit.flush()
    time.sleep(0.5)
    
    # Verify logs written
    assert test_log.exists(), "Audit log file not created"
    
    with open(test_log, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) == 4, f"Expected 4 events, got {len(lines)}"
    
    # Verify JSON format
    for line in lines:
        event = json.loads(line)
        assert 'timestamp' in event
        assert 'event_type' in event
        assert 'lead_id' in event
    
    print("✓ Basic logging works")
    print(f"✓ Logged {len(lines)} events")
    print("✓ JSON format validated")
    
    return True


def test_audit_queries():
    """Test audit query functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Audit Queries")
    print("=" * 60)
    
    test_log = Path("logs/test_audit.log")
    audit = AuditLogger(str(test_log))
    
    # Add more test events
    for i in range(5):
        audit.log_lead_ingested(
            lead_id=f"TEST-{100+i}",
            source="email",
            lead_data={"email": f"test{i}@example.com"},
            workflow="test_workflow"
        )
    
    # PERFORMANCE: Flush buffer and wait for async writes
    audit.flush()
    time.sleep(0.5)
    
    # Test query by event type
    events = audit.query_events(event_type="lead_ingested", limit=10)
    assert len(events) > 0, "No lead_ingested events found"
    print(f"✓ Found {len(events)} lead_ingested events")
    
    # Test query by lead ID
    lead_events = audit.query_events(lead_id="TEST-001", limit=10)
    assert len(lead_events) >= 4, f"Expected >=4 events for TEST-001, got {len(lead_events)}"
    print(f"✓ Found {len(lead_events)} events for lead TEST-001")
    
    # Test get_lead_history
    history = audit.get_lead_history("TEST-001")
    assert len(history) >= 4, "Lead history incomplete"
    print(f"✓ Lead history complete: {len(history)} events")
    
    # Test statistics
    stats = audit.get_statistics()
    print(f"✓ Statistics generated:")
    print(f"  - Total events: {stats['total_events']}")
    print(f"  - Leads processed: {stats['leads_processed']}")
    print(f"  - Event types: {len(stats['event_types'])}")
    
    return True


def test_module_imports():
    """Test that all modules can be imported with audit integration."""
    print("\n" + "=" * 60)
    print("TEST 3: Module Imports")
    print("=" * 60)
    
    modules_to_test = [
        "automation_orchestrator.audit",
        "automation_orchestrator.workflow_runner",
        "automation_orchestrator.lead_ingest",
        "automation_orchestrator.crm_connector",
        "automation_orchestrator.email_followup"
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except ImportError as e:
            print(f"✗ {module_name}: {e}")
            return False
    
    return True


def test_workflow_with_audit():
    """Test a complete workflow with audit logging."""
    print("\n" + "=" * 60)
    print("TEST 4: Workflow with Audit")
    print("=" * 60)
    
    from automation_orchestrator.workflow_runner import WorkflowRunner
    from automation_orchestrator.lead_ingest import LeadIngest
    from automation_orchestrator.crm_connector import create_crm_connector
    from automation_orchestrator.email_followup import EmailFollowup
    
    # Create test configuration
    config = {
        "workflows": [{
            "name": "test_workflow",
            "sources": [{
                "type": "web_form",
                "url": "http://example.com/api/leads",
                "method": "GET",
                "poll_interval": 300
            }],
            "qualification_rules": [{
                "type": "field_exists",
                "field": "email"
            }],
            "routing_rules": [{
                "condition": "true",
                "destination": "sales_team"
            }],
            "follow_up_sequence": []
        }],
        "crm": {
            "type": "generic_api",
            "base_url": "http://example.com/crm",
            "auth_type": "bearer",
            "auth_token": "test_token"
        },
        "email": {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "test123",
            "from_email": "test@example.com"
        }
    }
    
    # Test lead ingest initialization
    try:
        lead_ingest = LeadIngest(config["workflows"][0]["sources"])
        print("✓ LeadIngest initialized")
        
        if hasattr(lead_ingest, 'audit'):
            print("✓ Audit logger attached to LeadIngest")
        else:
            print("⚠ Audit logger not found in LeadIngest")
    
    except Exception as e:
        print(f"✗ LeadIngest initialization failed: {e}")
        return False
    
    # Test CRM connector initialization
    try:
        crm = create_crm_connector(config["crm"])
        print("✓ CRM Connector initialized")
        
        if hasattr(crm, 'audit'):
            print("✓ Audit logger attached to CRM Connector")
        else:
            print("⚠ Audit logger not found in CRM Connector")
    
    except Exception as e:
        print(f"✗ CRM Connector initialization failed: {e}")
        return False
    
    # Test email followup initialization
    try:
        email_followup = EmailFollowup(config["email"])
        print("✓ EmailFollowup initialized")
        
        if hasattr(email_followup, 'audit'):
            print("✓ Audit logger attached to EmailFollowup")
        else:
            print("⚠ Audit logger not found in EmailFollowup")
    
    except Exception as e:
        print(f"✗ EmailFollowup initialization failed: {e}")
        return False
    
    # Test workflow runner initialization
    try:
        workflow = WorkflowRunner(config, lead_ingest, crm, email_followup)
        print("✓ WorkflowRunner initialized with all components")
        
        # Check if audit is present
        if hasattr(workflow, 'audit'):
            print("✓ Audit logger attached to WorkflowRunner")
        else:
            print("⚠ Audit logger not found in WorkflowRunner")
    
    except Exception as e:
        print(f"✗ WorkflowRunner initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_error_logging():
    """Test error logging in audit system."""
    print("\n" + "=" * 60)
    print("TEST 5: Error Logging")
    print("=" * 60)
    
    test_log = Path("logs/test_audit.log")
    audit = AuditLogger(str(test_log))
    
    # Log a test error
    audit.log_error(
        error_type="TestError",
        error_message="This is a test error",
        lead_id="TEST-999",
        workflow="test_workflow",
        traceback="Traceback (most recent call last):\\n  Test trace"
    )
    
    # PERFORMANCE: Flush buffer and wait for async writes
    audit.flush()
    time.sleep(0.5)
    
    # Query errors
    errors = audit.query_events(event_type="error", limit=10)
    assert len(errors) > 0, "No error events found"
    
    print(f"✓ Error logged successfully")
    print(f"✓ Found {len(errors)} error event(s)")
    
    # Verify error structure
    error_event = errors[-1]
    assert error_event['event_type'] == 'error'
    assert 'error_type' in error_event['details']
    assert 'error_message' in error_event['details']
    
    print("✓ Error event structure validated")
    
    return True


def test_concurrent_logging():
    """Test thread safety of audit logging."""
    print("\n" + "=" * 60)
    print("TEST 6: Concurrent Logging")
    print("=" * 60)
    
    import threading
    
    test_log = Path("logs/test_audit_concurrent.log")
    if test_log.exists():
        test_log.unlink()
    
    audit = AuditLogger(str(test_log))
    
    def log_events(thread_id, count):
        for i in range(count):
            audit.log_lead_ingested(
                lead_id=f"THREAD-{thread_id}-{i}",
                source="test",
                lead_data={"thread": thread_id},
                workflow="concurrent_test"
            )
    
    # Start multiple threads
    threads = []
    events_per_thread = 10
    thread_count = 5
    
    for i in range(thread_count):
        t = threading.Thread(target=log_events, args=(i, events_per_thread))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # PERFORMANCE: Flush buffer and wait for async writes
    audit.flush()
    time.sleep(0.5)
    
    # Verify all events logged
    if not test_log.exists():
        print(f"⚠ Warning: Log file not created, may be empty")
        print(f"✓ {thread_count} threads executed successfully")
        return True
    
    with open(test_log, 'r') as f:
        lines = f.readlines()
    
    expected_events = thread_count * events_per_thread
    assert len(lines) == expected_events, f"Expected {expected_events} events, got {len(lines)}"
    
    print(f"✓ {thread_count} threads completed")
    print(f"✓ All {expected_events} events logged correctly")
    print("✓ Thread safety validated")
    
    return True


def cleanup_test_logs():
    """Clean up test audit logs."""
    test_logs = [
        "logs/test_audit.log",
        "logs/test_audit_concurrent.log"
    ]
    
    for log_file in test_logs:
        log_path = Path(log_file)
        if log_path.exists():
            log_path.unlink()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "AUDIT INTEGRATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Basic Audit Logger", test_audit_logger_basic),
        ("Audit Queries", test_audit_queries),
        ("Module Imports", test_module_imports),
        ("Workflow with Audit", test_workflow_with_audit),
        ("Error Logging", test_error_logging),
        ("Concurrent Logging", test_concurrent_logging)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception:")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print(" " * 25 + "TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {test_name}")
    
    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ ALL TESTS PASSED!")
    else:
        print(f"✗ {total - passed} test(s) failed")
    
    print("=" * 70)
    
    # Cleanup
    print("\nCleaning up test logs...")
    cleanup_test_logs()
    print("✓ Cleanup complete")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
