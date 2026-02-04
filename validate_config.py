"""
Configuration validator for audit system.
Validates settings, permissions, and benchmarks performance.
"""

import sys
import time
import os
from pathlib import Path
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger, AuditLogger
import automation_orchestrator.audit as audit_module


class ConfigValidator:
    """Validate audit system configuration."""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("AUDIT SYSTEM CONFIGURATION VALIDATOR")
        print("=" * 70)
        print()
        
        checks = [
            ("Configuration Constants", self.check_constants),
            ("File Permissions", self.check_permissions),
            ("Dependencies", self.check_dependencies),
            ("Write Performance", self.check_write_performance),
            ("Query Performance", self.check_query_performance),
            ("Memory Usage", self.check_memory_usage),
            ("Security Features", self.check_security_features)
        ]
        
        for name, check_func in checks:
            print(f"\n{'─' * 70}")
            print(f"Checking: {name}")
            print('─' * 70)
            
            try:
                check_func()
            except Exception as e:
                self._fail(f"Check raised exception: {e}")
        
        # Summary
        print(f"\n{'=' * 70}")
        print("VALIDATION SUMMARY")
        print('=' * 70)
        print(f"✅ Passed:   {self.checks_passed}")
        print(f"❌ Failed:   {self.checks_failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print()
        
        if self.checks_failed > 0:
            print("❌ VALIDATION FAILED - Fix errors before deployment")
            return False
        elif self.warnings > 0:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Review warnings")
            return True
        else:
            print("✅ VALIDATION PASSED - Configuration is ready for production")
            return True
    
    def check_constants(self):
        """Check configuration constants."""
        # Check buffer size
        buffer_size = audit_module.WRITE_BUFFER_SIZE
        if buffer_size < 10:
            self._warn(f"WRITE_BUFFER_SIZE too small: {buffer_size} (recommend 50-500)")
        elif buffer_size > 1000:
            self._warn(f"WRITE_BUFFER_SIZE very large: {buffer_size} (may use excess memory)")
        else:
            self._pass(f"WRITE_BUFFER_SIZE: {buffer_size} (good)")
        
        # Check flush interval
        flush_interval = audit_module.WRITE_FLUSH_INTERVAL
        if flush_interval < 0.5:
            self._warn(f"WRITE_FLUSH_INTERVAL too short: {flush_interval}s (may cause high I/O)")
        elif flush_interval > 30:
            self._warn(f"WRITE_FLUSH_INTERVAL too long: {flush_interval}s (high latency)")
        else:
            self._pass(f"WRITE_FLUSH_INTERVAL: {flush_interval}s (good)")
        
        # Check cache size
        cache_size = audit_module.QUERY_CACHE_SIZE
        if cache_size < 16:
            self._warn(f"QUERY_CACHE_SIZE too small: {cache_size} (recommend 64-256)")
        elif cache_size > 1000:
            self._warn(f"QUERY_CACHE_SIZE very large: {cache_size} (may use excess memory)")
        else:
            self._pass(f"QUERY_CACHE_SIZE: {cache_size} (good)")
        
        # Check compression level
        comp_level = audit_module.COMPRESSION_LEVEL
        if comp_level < 1 or comp_level > 9:
            self._fail(f"COMPRESSION_LEVEL invalid: {comp_level} (must be 1-9)")
        elif comp_level < 3:
            self._warn(f"COMPRESSION_LEVEL low: {comp_level} (poor compression)")
        elif comp_level > 7:
            self._warn(f"COMPRESSION_LEVEL high: {comp_level} (slow compression)")
        else:
            self._pass(f"COMPRESSION_LEVEL: {comp_level} (good)")
        
        # Check memory limit
        mem_limit = audit_module.MAX_MEMORY_EVENTS
        if mem_limit < 1000:
            self._warn(f"MAX_MEMORY_EVENTS too small: {mem_limit} (may truncate stats)")
        elif mem_limit > 100000:
            self._warn(f"MAX_MEMORY_EVENTS very large: {mem_limit} (may use excess memory)")
        else:
            self._pass(f"MAX_MEMORY_EVENTS: {mem_limit} (good)")
        
        # Check size limits
        max_size = audit_module.MAX_DETAILS_SIZE
        if max_size < 1024:
            self._warn(f"MAX_DETAILS_SIZE too small: {max_size} bytes")
        elif max_size > 1024 * 1024:
            self._warn(f"MAX_DETAILS_SIZE very large: {max_size} bytes (DoS risk)")
        else:
            self._pass(f"MAX_DETAILS_SIZE: {max_size} bytes (good)")
    
    def check_permissions(self):
        """Check file system permissions."""
        # Check logs directory
        logs_dir = Path("logs")
        
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True)
                self._pass("Created logs directory")
            except Exception as e:
                self._fail(f"Cannot create logs directory: {e}")
                return
        
        # Check write permission
        test_file = logs_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            self._pass("Logs directory is writable")
        except Exception as e:
            self._fail(f"Logs directory not writable: {e}")
        
        # Check for existing audit log
        audit_log = logs_dir / "audit.log"
        if audit_log.exists():
            # Check if writable
            if os.access(audit_log, os.W_OK):
                self._pass(f"Existing audit log is writable: {audit_log}")
            else:
                self._fail(f"Existing audit log not writable: {audit_log}")
            
            # Check size
            size_mb = audit_log.stat().st_size / (1024 * 1024)
            if size_mb > 1000:
                self._warn(f"Audit log is large: {size_mb:.1f} MB (consider rotation)")
            else:
                self._pass(f"Audit log size: {size_mb:.1f} MB")
        else:
            self._pass("No existing audit log (will be created)")
    
    def check_dependencies(self):
        """Check required dependencies."""
        required = [
            ("requests", "HTTP webhooks"),
            ("loguru", "Enhanced logging"),
            ("jsonschema", "JSON validation")
        ]
        
        for module_name, purpose in required:
            try:
                __import__(module_name)
                self._pass(f"{module_name} installed ({purpose})")
            except ImportError:
                self._fail(f"{module_name} not installed ({purpose})")
    
    def check_write_performance(self):
        """Benchmark write performance."""
        print("Running write performance test (100 events)...")
        
        test_file = Path("logs/.validate_test.log")
        audit = AuditLogger(str(test_file))
        
        start = time.time()
        for i in range(100):
            audit.log_event("test", {"index": i}, lead_id=f"test_{i}")
        
        audit.flush()
        time.sleep(0.5)
        
        elapsed = time.time() - start
        throughput = 100 / elapsed
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        
        if throughput < 100:
            self._fail(f"Write throughput too low: {throughput:.0f} events/sec (target: >500)")
        elif throughput < 500:
            self._warn(f"Write throughput moderate: {throughput:.0f} events/sec (target: 500+)")
        else:
            self._pass(f"Write throughput: {throughput:.0f} events/sec")
    
    def check_query_performance(self):
        """Benchmark query performance."""
        print("Running query performance test...")
        
        test_file = Path("logs/.validate_test.log")
        audit = AuditLogger(str(test_file))
        
        # Create test data
        for i in range(100):
            audit.log_event("test", {"index": i}, lead_id=f"test_{i % 10}")
        audit.flush()
        time.sleep(0.5)
        
        # Test query
        start = time.time()
        results = audit.query_events(event_type="test", limit=50)
        elapsed = (time.time() - start) * 1000  # ms
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        
        if elapsed > 100:
            self._warn(f"Query time high: {elapsed:.1f}ms (target: <50ms)")
        else:
            self._pass(f"Query time: {elapsed:.1f}ms")
        
        # Check cache
        if len(audit.query_cache) > 0:
            self._pass(f"Query cache working: {len(audit.query_cache)} entries")
        else:
            self._warn("Query cache not populated (may be disabled)")
    
    def check_memory_usage(self):
        """Check memory usage characteristics."""
        print("Checking memory usage with 1000 events...")
        
        test_file = Path("logs/.validate_test.log")
        audit = AuditLogger(str(test_file))
        
        # Create larger dataset
        for i in range(1000):
            audit.log_event("test", {"data": "x" * 100}, lead_id=f"test_{i}")
        audit.flush()
        time.sleep(0.5)
        
        # Check buffer size
        buffer_size = audit.write_buffer.qsize()
        if buffer_size > 100:
            self._warn(f"Write buffer has {buffer_size} pending events")
        else:
            self._pass(f"Write buffer size: {buffer_size} events")
        
        # Check statistics
        stats = audit.get_statistics()
        if stats['total_events'] < 1000:
            self._warn(f"Only {stats['total_events']} events counted (expected 1000)")
        else:
            self._pass(f"Statistics working: {stats['total_events']} events")
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    def check_security_features(self):
        """Check security features."""
        # Check rate limiting
        if hasattr(audit_module, 'RATE_LIMIT_REQUESTS'):
            self._pass("Rate limiting configured")
        else:
            self._warn("Rate limiting configuration not found")
        
        # Check validation functions
        test_file = Path("logs/.validate_test.log")
        audit = AuditLogger(str(test_file))
        
        # Test path validation
        try:
            audit._validate_audit_path("../../../etc/passwd")
            self._fail("Path traversal not blocked")
        except ValueError:
            self._pass("Path traversal protection working")
        
        # Test input sanitization
        test_str = audit._sanitize_string("test\x00\x01\x02", 100)
        if '\x00' in test_str or '\x01' in test_str:
            self._fail("Control character sanitization not working")
        else:
            self._pass("Input sanitization working")
        
        # Test size validation
        try:
            large_dict = {"data": "x" * 100000}  # 100KB
            audit._validate_details_size(large_dict)
            self._fail("Size validation not blocking large events")
        except ValueError:
            self._pass("Size validation working")
        
        # Test SSRF protection
        try:
            audit._validate_url("http://localhost:8080", "webhook")
            self._fail("SSRF protection not blocking localhost")
        except ValueError:
            self._pass("SSRF protection working")
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    def _pass(self, message: str):
        """Mark check as passed."""
        print(f"  ✅ {message}")
        self.checks_passed += 1
    
    def _fail(self, message: str):
        """Mark check as failed."""
        print(f"  ❌ {message}")
        self.checks_failed += 1
    
    def _warn(self, message: str):
        """Mark check as warning."""
        print(f"  ⚠️  {message}")
        self.warnings += 1


def main():
    """Run configuration validator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate audit system configuration")
    parser.add_argument("--quick", action="store_true",
                       help="Skip performance benchmarks")
    
    args = parser.parse_args()
    
    validator = ConfigValidator()
    
    if args.quick:
        print("Running quick validation (skipping performance tests)...")
        validator.check_constants()
        validator.check_permissions()
        validator.check_dependencies()
        validator.check_security_features()
        
        success = validator.checks_failed == 0
    else:
        success = validator.validate_all()
    
    # Exit with appropriate code
    if not success:
        sys.exit(1)
    elif validator.warnings > 0:
        sys.exit(0)  # Warnings are OK for now
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
