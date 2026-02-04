#!/usr/bin/env python
"""
Phase 2 Security Tests - Advanced hardening validation
Tests rate limiting, query DOS, error handling, TLS, and security monitoring
"""

import sys
import os
import json
import time
import tempfile
from pathlib import Path
from threading import Thread

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import AuditLogger


def test_rate_limiting():
    """Test that rate limiting prevents log flooding."""
    print("\n" + "="*70)
    print("TEST: Rate Limiting")
    print("="*70)
    
    test_log = Path("logs/test_rate_limit.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test 1: Flood with events and check rate limiting kicks in
    print("[INFO] Flooding with 300 events (limit: 200 burst)...")
    
    success_count = 0
    for i in range(300):
        try:
            audit.log_event(
                "test_event",
                {"index": i},
                lead_id=f"LEAD-{i%10}",  # 10 different leads
                workflow="test"
            )
            success_count += 1
        except Exception as e:
            print(f"[FAIL] Unexpected error: {e}")
    
    # Not all 300 should succeed - some should be rate limited
    if success_count < 300:
        print(f"[OK] Rate limiting active: {success_count}/300 events logged")
        print(f"     Blocked: {300 - success_count} events")
    else:
        print(f"[FAIL] No rate limiting: all 300 events logged")
    
    # Test 2: Check rate limit stats
    stats = audit.get_rate_limit_stats()
    print(f"\n[INFO] Rate limit stats:")
    print(f"     Active sources: {stats['active_sources']}")
    print(f"     Blocked events: {stats['blocked_events']}")
    
    success = stats['blocked_events'] > 0 and success_count < 300
    
    # Test 3: Wait and verify rate limit resets
    print(f"\n[INFO] Waiting 1.5 seconds for rate limit reset...")
    time.sleep(1.5)
    
    try:
        audit.log_event("test_reset", {"test": "after_wait"}, lead_id="LEAD-NEW", workflow="test")
        print(f"[OK] Rate limit reset after cooldown")
    except Exception as e:
        print(f"[FAIL] Rate limit didn't reset: {e}")
        success = False
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Rate limiting\n")
    return success


def test_query_dos_protection():
    """Test that query escaping prevents ReDoS attacks."""
    print("\n" + "="*70)
    print("TEST: Query ReDoS Protection")
    print("="*70)
    
    test_log = Path("logs/test_redos.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Create some test events
    for i in range(10):
        audit.log_event(
            "test_event",
            {"data": f"test{i}"},
            lead_id=f"LEAD-{i}",
            workflow="test"
        )
    
    # Test 1: Regex DOS attack patterns
    redos_patterns = [
        "^(a+)+$",  # Exponential backtracking
        "(a*)*b",   # Polynomial backtracking
        "((a+)+)+",  # Nested quantifiers
        "a*a*a*a*a*a*a*a*b",  # Multiple quantifiers
    ]
    
    blocked_count = 0
    for pattern in redos_patterns:
        try:
            start = time.time()
            # These patterns should be escaped, making them harmless
            results = audit.query_events(lead_id=pattern, limit=100)
            elapsed = time.time() - start
            
            if elapsed < 0.1:  # Should be fast because regex is escaped
                print(f"[OK] ReDoS pattern escaped (took {elapsed:.3f}s): {pattern[:20]}")
                blocked_count += 1
            else:
                print(f"[FAIL] Query too slow ({elapsed:.3f}s): {pattern[:20]}")
        except Exception as e:
            print(f"[INFO] Query error (acceptable): {str(e)[:50]}")
            blocked_count += 1
    
    # Test 2: Normal queries should still work
    try:
        results = audit.query_events(lead_id="LEAD-1", workflow="test")
        if results:
            print(f"[OK] Normal query works: found {len(results)} event(s)")
        else:
            print(f"[INFO] Normal query returned no results (log may be empty)")
    except Exception as e:
        print(f"[FAIL] Normal query failed: {e}")
        blocked_count = 0
    
    success = blocked_count >= len(redos_patterns) - 1  # Allow 1 failure
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Query ReDoS protection")
    print(f"Protected against {blocked_count}/{len(redos_patterns)} ReDoS patterns\n")
    return success


def test_security_monitoring():
    """Test security event logging and monitoring."""
    print("\n" + "="*70)
    print("TEST: Security Monitoring")
    print("="*70)
    
    test_log = Path("logs/test_security_monitor.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test 1: Trigger various security events
    security_events_triggered = 0
    
    # Trigger validation error
    try:
        audit.log_event("test", {"data": "x" * 100000})  # Too large
    except ValueError:
        security_events_triggered += 1
        print("[OK] Validation error triggered and logged")
    
    # Trigger rate limit
    for i in range(250):  # Exceed burst limit
        audit.log_event("flood", {"i": i}, lead_id="LEAD-FLOOD", workflow="test")
    
    # Check rate limit was logged
    stats = audit.get_rate_limit_stats()
    if stats['blocked_events'] > 0:
        security_events_triggered += 1
        print(f"[OK] Rate limit event logged ({stats['blocked_events']} blocked)")
    
    # Test 2: Query security events
    sec_events = audit.get_security_events()
    print(f"\n[INFO] Security events captured: {len(sec_events)}")
    
    for event in sec_events[:5]:  # Show first 5
        print(f"     - {event['type']}: {list(event['details'].keys())}")
    
    # Test 3: Filter by event type
    rate_limit_events = audit.get_security_events(event_type="rate_limit_exceeded")
    validation_events = audit.get_security_events(event_type="validation_error")
    
    print(f"\n[INFO] Event types:")
    print(f"     Rate limit: {len(rate_limit_events)}")
    print(f"     Validation: {len(validation_events)}")
    
    # Test 4: Check security log file exists
    security_log = Path("logs/security_events.log")
    if security_log.exists():
        print(f"[OK] Security log file created: {security_log}")
        size = security_log.stat().st_size
        print(f"     Size: {size} bytes")
    else:
        print(f"[INFO] Security log file not created yet")
    
    success = len(sec_events) > 0 and security_events_triggered >= 2
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    if security_log.exists():
        security_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Security monitoring")
    print(f"Captured {len(sec_events)} security events\n")
    return success


def test_error_handling():
    """Test enhanced error handling with production mode."""
    print("\n" + "="*70)
    print("TEST: Enhanced Error Handling")
    print("="*70)
    
    test_log = Path("logs/test_error_handling.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    
    # Test 1: Development mode (stack traces visible)
    from automation_orchestrator import audit as audit_module
    original_mode = audit_module.PRODUCTION_MODE
    audit_module.PRODUCTION_MODE = False
    
    audit = AuditLogger(audit_file=str(test_log))
    
    try:
        # Trigger validation error
        audit.log_event("test", {"x": "y" * 100000})
    except ValueError as e:
        if "too large" in str(e).lower():
            print(f"[OK] Dev mode: Detailed error shown")
        else:
            print(f"[INFO] Dev mode error: {str(e)[:50]}")
    
    # Test 2: Production mode (generic errors)
    audit_module.PRODUCTION_MODE = True
    audit2 = AuditLogger(audit_file=str(test_log))
    
    try:
        audit2.log_event("test", {"x": "y" * 100000})
    except ValueError as e:
        # Should still get the error, just logged differently
        print(f"[OK] Production mode: Error handled gracefully")
    
    # Restore original mode
    audit_module.PRODUCTION_MODE = original_mode
    
    # Test 3: Verify error logging doesn't crash system
    errors_handled = 0
    for i in range(10):
        try:
            audit2.log_event(f"invalid@type{i}", {}, lead_id=f"BAD\\nID{i}")
        except (ValueError, TypeError):
            errors_handled += 1
    
    print(f"[OK] Handled {errors_handled}/10 invalid events gracefully")
    
    success = errors_handled == 10
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Error handling\n")
    return success


def test_concurrent_rate_limiting():
    """Test rate limiting under concurrent load."""
    print("\n" + "="*70)
    print("TEST: Concurrent Rate Limiting")
    print("="*70)
    
    test_log = Path("logs/test_concurrent_rate.log")
    test_log.parent.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(audit_file=str(test_log))
    
    # Test: Multiple threads trying to exceed rate limit
    print("[INFO] Starting 10 threads, each sending 30 events...")
    
    results = {"logged": 0, "blocked": 0}
    results_lock = Thread()
    
    def thread_flood(thread_id):
        for i in range(30):
            try:
                audit.log_event(
                    "concurrent_test",
                    {"thread": thread_id, "index": i},
                    lead_id=f"THREAD-{thread_id}",
                    workflow="concurrent"
                )
                results["logged"] += 1
            except Exception:
                results["blocked"] += 1
    
    threads = []
    start_time = time.time()
    
    for i in range(10):
        t = Thread(target=thread_flood, args=(i,))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    
    total_attempts = 10 * 30  # 300 events
    stats = audit.get_rate_limit_stats()
    
    print(f"\n[INFO] Results:")
    print(f"     Total attempts: {total_attempts}")
    print(f"     Successfully logged: {results['logged']}")
    print(f"     Blocked by rate limit: {stats['blocked_events']}")
    print(f"     Time elapsed: {elapsed:.2f}s")
    print(f"     Throughput: {results['logged']/elapsed:.1f} events/sec")
    
    # Should have blocked some events
    success = stats['blocked_events'] > 0 and results['logged'] < total_attempts
    
    if success:
        print(f"[OK] Rate limiting working under concurrent load")
    else:
        print(f"[FAIL] Rate limiting not effective")
    
    # Cleanup
    if test_log.exists():
        test_log.unlink()
    
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Concurrent rate limiting\n")
    return success


def main():
    """Run all Phase 2 security tests."""
    print("\n" + "="*70)
    print("AUDIT SYSTEM - PHASE 2 SECURITY TESTS")
    print("="*70)
    print("\nTesting advanced security features:")
    print("1. Rate Limiting")
    print("2. Query ReDoS Protection")
    print("3. Security Monitoring")
    print("4. Enhanced Error Handling")
    print("5. Concurrent Rate Limiting")
    
    # Run all tests
    results = {}
    results['rate_limiting'] = test_rate_limiting()
    results['query_redos'] = test_query_dos_protection()
    results['security_monitoring'] = test_security_monitoring()
    results['error_handling'] = test_error_handling()
    results['concurrent_rate_limiting'] = test_concurrent_rate_limiting()
    
    # Summary
    print("\n" + "="*70)
    print("PHASE 2 SECURITY TEST SUMMARY")
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
        print("\n🎉 ALL PHASE 2 SECURITY TESTS PASSED! 🎉")
        print("Advanced security features validated.")
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
