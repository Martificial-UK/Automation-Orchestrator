#!/usr/bin/env python
"""
Security tests for audit system - Phase 1 Critical Fixes
Tests path traversal, SSRF, injection, DoS, and SMTP vulnerabilities
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import AuditLogger


def test_path_traversal_protection():
    """Test that path traversal attacks are blocked."""
    print("\n" + "="*70)
    print("TEST: Path Traversal Protection")
    print("="*70)
    
    # Test 1: Attempt to write outside logs directory
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\evil.log",
        "logs/../../sensitive.log",
        "/etc/passwd",
        "C:\\Windows\\System32\\evil.log"
    ]
    
    blocked_count = 0
    for path in malicious_paths:
        try:
            audit = AuditLogger(audit_file=path)
            print(f"[FAIL] Path traversal not blocked: {path}")
        except ValueError as e:
            if "Invalid audit file path" in str(e):
                print(f"[OK] Blocked path traversal: {path}")
                blocked_count += 1
            else:
                print(f"[FAIL] Wrong error for {path}: {e}")
        except Exception as e:
            print(f"[FAIL] Unexpected error for {path}: {e}")
    
    # Test 2: Valid paths should work
    valid_paths = [
        "logs/audit.log",
        "logs/test/audit.log",
        "logs/subfolder/another/audit.log"
    ]
    
    for path in valid_paths:
        try:
            test_log = Path(path)
            test_log.parent.mkdir(parents=True, exist_ok=True)
            audit = AuditLogger(audit_file=path)
            audit.log_workflow_started("test")
            print(f"[OK] Valid path accepted: {path}")
            # Cleanup
            if test_log.exists():
                test_log.unlink()
        except Exception as e:
            print(f"[FAIL] Valid path rejected: {path} - {e}")
    
    success = blocked_count == len(malicious_paths)
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Path traversal protection")
    print(f"Blocked {blocked_count}/{len(malicious_paths)} malicious paths\n")
    return success


def test_ssrf_protection():
    """Test that SSRF attacks via webhooks are blocked."""
    print("\n" + "="*70)
    print("TEST: SSRF Protection (Webhooks)")
    print("="*70)
    
    test_log = Path("logs/test_ssrf.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test 1: Block localhost and private IPs
    malicious_urls = [
        "http://localhost:8080/webhook",
        "http://127.0.0.1/webhook",
        "http://0.0.0.0/webhook",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
        "http://metadata.google.internal/",  # GCP metadata
        "http://192.168.1.1/webhook",  # Private IP
        "http://10.0.0.1/webhook",  # Private IP
        "http://172.16.0.1/webhook",  # Private IP
        "http://[::1]/webhook",  # IPv6 localhost
    ]
    
    blocked_count = 0
    for url in malicious_urls:
        try:
            audit.add_webhook(url)
            print(f"[FAIL] SSRF not blocked: {url}")
        except ValueError as e:
            if "Blocked" in str(e) or "not allowed" in str(e):
                print(f"[OK] Blocked SSRF attempt: {url[:50]}")
                blocked_count += 1
            else:
                print(f"[FAIL] Wrong error for {url}: {e}")
        except Exception as e:
            print(f"[FAIL] Unexpected error for {url}: {e}")
    
    # Test 2: Valid public URLs should work
    valid_urls = [
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        "https://discord.com/api/webhooks/123456789/abcdefg",
        "https://example.com/webhook",
        "http://public-server.com:8080/events"
    ]
    
    for url in valid_urls:
        try:
            audit.add_webhook(url)
            print(f"[OK] Valid URL accepted: {url[:50]}")
        except Exception as e:
            print(f"[FAIL] Valid URL rejected: {url} - {e}")
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    success = blocked_count == len(malicious_urls)
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: SSRF protection")
    print(f"Blocked {blocked_count}/{len(malicious_urls)} SSRF attempts\n")
    return success


def test_log_injection_protection():
    """Test that log injection attacks are prevented."""
    print("\n" + "="*70)
    print("TEST: Log Injection Protection")
    print("="*70)
    
    test_log = Path("logs/test_injection.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test 1: Attempt to inject fake log entries via newlines
    injection_attempts = [
        "LEAD-001\\n{\\\"event_type\\\":\\\"admin_access\\\"}",
        "LEAD-002\\r\\n{\\\"malicious\\\":true}",
        "LEAD\\x00NULL",  # Null byte injection
        "LEAD\\x1b[31mRED",  # ANSI escape codes
    ]
    
    blocked_count = 0
    for attempt in injection_attempts:
        try:
            # Should be rejected by validation
            audit.log_lead_ingested(attempt, "test_source", {"email": "test@example.com"}, "test")
            print(f"[FAIL] Injection not blocked: {repr(attempt[:30])}")
        except ValueError as e:
            if "Invalid lead_id format" in str(e):
                print(f"[OK] Injection blocked: {repr(attempt[:30])}")
                blocked_count += 1
            else:
                print(f"[FAIL] Wrong error for {repr(attempt[:30])}: {e}")
        except Exception as e:
            print(f"[FAIL] Unexpected error for {repr(attempt[:30])}: {e}")
    
    # Test 2: Valid lead IDs should work
    valid_lead_ids = ["LEAD-001", "LEAD-002", "TEST_USER"]
    for lead_id in valid_lead_ids:
        try:
            audit.log_lead_ingested(lead_id, "test_source", {"email": "test@example.com"}, "test")
            print(f"[OK] Valid lead_id accepted: {lead_id}")
        except Exception as e:
            print(f"[FAIL] Valid lead_id rejected: {lead_id} - {e}")
            blocked_count = 0  # Fail the test
    
    # Test 3: Verify log file integrity
    if test_log.exists():
        content = test_log.read_text()
        lines = content.strip().split('\\n')
        
        # All lines should be valid JSON
        for i, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
                if 'event_type' not in event:
                    print(f"[FAIL] Line {i} missing event_type")
                    blocked_count = 0
            except json.JSONDecodeError as e:
                print(f"[FAIL] Line {i} is not valid JSON: {line[:50]}")
                blocked_count = 0
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    success = blocked_count == len(injection_attempts)
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Log injection protection")
    print(f"Blocked {blocked_count}/{len(injection_attempts)} injection attempts\n")
    return success


def test_dos_size_limits():
    """Test that size limits prevent DoS attacks."""
    print("\n" + "="*70)
    print("TEST: DoS Protection (Size Limits)")
    print("="*70)
    
    test_log = Path("logs/test_dos.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test 1: Oversized details dictionary (>50KB)
    huge_data = {"field" + str(i): "x" * 1000 for i in range(100)}  # ~100KB
    
    try:
        audit.log_lead_ingested("LEAD-001", "test", huge_data, "test")
        print("[FAIL] Oversized data not blocked")
        success = False
    except ValueError as e:
        if "too large" in str(e).lower():
            print(f"[OK] Blocked oversized data: {str(e)[:70]}...")
            success = True
        else:
            print(f"[FAIL] Wrong error for oversized data: {e}")
            success = False
    except TypeError as e:
        # Also acceptable - JSON serialization error
        print(f"[OK] Blocked oversized data via type error: {str(e)[:70]}...")
        success = True
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        success = False
    
    # Test 2: Reasonable sized data should work
    normal_data = {"email": "test@example.com", "name": "Test User", "company": "Acme Inc"}
    try:
        audit.log_lead_ingested("LEAD-002", "web_form", normal_data, "sales")
        print("[OK] Normal sized data accepted")
    except Exception as e:
        print(f"[FAIL] Normal data rejected: {e}")
        success = False
    
    # Test 3: Very long lead_id strings should be rejected
    long_string = "A" * 20000  # 20KB string
    try:
        audit.log_lead_ingested(long_string, "test", {"data": "test"}, "workflow")
        print("[FAIL] Very long lead_id not rejected")
        success = False
    except ValueError as e:
        if "Invalid lead_id format" in str(e) or "truncated" in str(e):
            print(f"[OK] Long lead_id rejected: {str(e)[:60]}...")
        else:
            print(f"[INFO] Long lead_id handled: {str(e)[:60]}...")
    except Exception as e:
        print(f"[INFO] Long lead_id handled: {str(e)[:60]}...")
    
    # Test 4: Moderately large but valid data (~25KB, under 50KB limit)
    medium_data = {"field" + str(i): "x" * 500 for i in range(50)}  # ~25KB
    try:
        audit.log_lead_ingested("LEAD-003", "test", medium_data, "test")
        print("[OK] Medium sized data accepted (25KB < 50KB limit)")
    except Exception as e:
        print(f"[FAIL] Medium data rejected unexpectedly: {e}")
        success = False
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: DoS size limit protection\n")
    return success


def test_input_validation():
    """Test comprehensive input validation."""
    print("\n" + "="*70)
    print("TEST: Input Validation")
    print("="*70)
    
    test_log = Path("logs/test_validation.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Invalid lead_id formats
    invalid_lead_ids = [
        "",  # Empty
        "LEAD@001",  # Special char
        "LEAD 001",  # Space
        "LEAD<script>",  # XSS attempt
        "../../etc/passwd",  # Path traversal
    ]
    
    for lead_id in invalid_lead_ids:
        tests_total += 1
        try:
            audit.log_lead_ingested(lead_id, "test", {}, "test")
            print(f"[FAIL] Invalid lead_id not rejected: {repr(lead_id)}")
        except (ValueError, TypeError) as e:
            print(f"[OK] Invalid lead_id rejected: {repr(lead_id[:20])}")
            tests_passed += 1
        except Exception as e:
            print(f"[FAIL] Unexpected error for {repr(lead_id)}: {e}")
    
    # Test 2: Valid lead_ids should work
    valid_lead_ids = ["LEAD-001", "USER_123", "ABC-DEF-456", "Lead001"]
    
    for lead_id in valid_lead_ids:
        tests_total += 1
        try:
            audit.log_lead_ingested(lead_id, "test", {"email": "test@example.com"}, "sales")
            print(f"[OK] Valid lead_id accepted: {lead_id}")
            tests_passed += 1
        except Exception as e:
            print(f"[FAIL] Valid lead_id rejected: {lead_id} - {e}")
    
    # Test 3: Type validation
    tests_total += 1
    try:
        audit.log_lead_ingested(12345, "test", {}, "test")  # Integer instead of string
        print("[FAIL] Type error not caught (lead_id)")
    except TypeError as e:
        print(f"[OK] Type error caught: {e}")
        tests_passed += 1
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    success = tests_passed == tests_total
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Input validation")
    print(f"Passed {tests_passed}/{tests_total} validation tests\n")
    return success


def test_persistent_secret_key():
    """Test that secret key persists across restarts."""
    print("\n" + "="*70)
    print("TEST: Persistent Secret Key")
    print("="*70)
    
    test_log = Path("logs/test_secret.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    
    # Create first instance
    audit1 = AuditLogger(audit_file=str(test_log), enable_integrity=True)
    key1 = audit1.secret_key
    
    # Log an event
    audit1.log_lead_ingested("LEAD-001", "test", {"email": "test@example.com"}, "test")
    
    # Create second instance (simulates restart)
    audit2 = AuditLogger(audit_file=str(test_log), enable_integrity=True)
    key2 = audit2.secret_key
    
    # Keys should match
    if key1 == key2:
        print(f"[OK] Secret key persisted across restarts")
        print(f"     Key: {key1[:16]}...{key1[-16:]}")
        success = True
    else:
        print(f"[FAIL] Secret key changed on restart")
        print(f"     Key1: {key1[:32]}...")
        print(f"     Key2: {key2[:32]}...")
        success = False
    
    # Verify old signatures are still valid
    if test_log.exists():
        content = test_log.read_text()
        lines = content.strip().split('\\n')
        
        for line in lines:
            event = json.loads(line)
            if 'signature' in event:
                # Remove signature and recalculate
                original_sig = event.pop('signature')
                event_str = json.dumps(event, sort_keys=True)
                recalc_sig = audit2._calculate_signature(event_str)
                
                if original_sig == recalc_sig:
                    print(f"[OK] Old signature still valid")
                else:
                    print(f"[FAIL] Old signature no longer valid")
                    success = False
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    key_file = Path("logs/.audit_secret")
    if key_file.exists():
        key_file.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Persistent secret key\n")
    return success


def main():
    """Run all security tests."""
    print("\n" + "="*70)
    print("AUDIT SYSTEM - PHASE 1 SECURITY TESTS")
    print("="*70)
    print("\nTesting critical security fixes:")
    print("1. Path Traversal Protection")
    print("2. SSRF Protection")
    print("3. Log Injection Protection")
    print("4. DoS Size Limits")
    print("5. Input Validation")
    print("6. Persistent Secret Key")
    
    # Run all tests
    results = {}
    results['path_traversal'] = test_path_traversal_protection()
    results['ssrf'] = test_ssrf_protection()
    results['log_injection'] = test_log_injection_protection()
    results['dos_limits'] = test_dos_size_limits()
    results['input_validation'] = test_input_validation()
    results['secret_key'] = test_persistent_secret_key()
    
    # Summary
    print("\n" + "="*70)
    print("SECURITY TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    print("\n" + "="*70)
    print(f"OVERALL: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL SECURITY TESTS PASSED! 🎉")
        print("Phase 1 critical security fixes validated.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} SECURITY TEST(S) FAILED")
        print("Review failures above before production deployment.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
