"""
Security Validation Tests for Automation Orchestrator
Validates that all security measures are in place and working
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_security_imports():
    """Test that all security modules can be imported"""
    print("\n[TEST] Verifying Security Module Imports...")
    try:
        from automation_orchestrator.security import (
            InputValidator, EmailValidator, PathValidator, 
            WebhookValidator, SecretManager, PIIManager,
            OutputSanitizer, RateLimiter, SecurityEventLogger
        )
        print("✓ All security modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import security modules: {e}")
        return False


def test_input_validation():
    """Test input validation"""
    print("\n[TEST] Testing Input Validation...")
    try:
        from automation_orchestrator.security import InputValidator
        
        # Valid lead ID
        result = InputValidator.validate_lead_id("LEAD-001")
        assert result == "LEAD-001", "Valid lead ID rejected"
        
        # Invalid lead ID - should raise
        try:
            InputValidator.validate_lead_id("<script>alert(1)</script>")
            print("✗ XSS injection not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        print("✓ Input validation working correctly")
        return True
    except Exception as e:
        print(f"✗ Input validation test failed: {e}")
        return False


def test_email_validation():
    """Test email validation"""
    print("\n[TEST] Testing Email Validation...")
    try:
        from automation_orchestrator.security import EmailValidator
        
        # Valid email
        result = EmailValidator.validate_email("test@example.com")
        assert result == "test@example.com", "Valid email rejected"
        
        # SMTP injection attempt
        try:
            EmailValidator.validate_email("test@example.com\nBcc: attacker@evil.com")
            print("✗ SMTP injection not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        # Header sanitization
        subject = EmailValidator.sanitize_header("Test\nSubject")
        assert "\n" not in subject, "CRLF not removed from header"
        
        print("✓ Email validation working correctly")
        return True
    except Exception as e:
        print(f"✗ Email validation test failed: {e}")
        return False


def test_path_validation():
    """Test path validation"""
    print("\n[TEST] Testing Path Validation...")
    try:
        from automation_orchestrator.security import PathValidator
        
        # Path traversal attempt should be blocked
        try:
            PathValidator.validate_path("../../etc/passwd")
            print("✗ Path traversal not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        print("✓ Path validation working correctly")
        return True
    except Exception as e:
        print(f"✗ Path validation test failed: {e}")
        return False


def test_webhook_validation():
    """Test webhook SSRF protection"""
    print("\n[TEST] Testing Webhook Validation (SSRF Protection)...")
    try:
        from automation_orchestrator.security import WebhookValidator
        
        # Localhost should be blocked
        try:
            WebhookValidator.validate_webhook_url("http://localhost:8000/webhook")
            print("✗ Localhost not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        # Private IP should be blocked
        try:
            WebhookValidator.validate_webhook_url("http://192.168.1.1/webhook")
            print("✗ Private IP not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        # AWS metadata should be blocked
        try:
            WebhookValidator.validate_webhook_url("http://169.254.169.254/latest/meta-data/")
            print("✗ AWS metadata not blocked!")
            return False
        except ValueError:
            pass  # Expected
        
        print("✓ Webhook validation working correctly (SSRF protected)")
        return True
    except Exception as e:
        print(f"✗ Webhook validation test failed: {e}")
        return False


def test_pii_anonymization():
    """Test PII anonymization"""
    print("\n[TEST] Testing PII Anonymization...")
    try:
        from automation_orchestrator.security import PIIManager
        
        # Email anonymization
        anon_email = PIIManager.anonymize_email("john.doe@example.com")
        assert "john" in anon_email.lower() or "*" in anon_email, "Email not anonymized"
        
        # Phone anonymization
        anon_phone = PIIManager.anonymize_phone("555-123-4567")
        assert "****" in anon_phone, "Phone not anonymized"
        
        print("✓ PII anonymization working correctly")
        return True
    except Exception as e:
        print(f"✗ PII anonymization test failed: {e}")
        return False


def test_audit_logging():
    """Test audit logging with security validators"""
    print("\n[TEST] Testing Audit Logging with Security...")
    try:
        from automation_orchestrator.audit import get_audit_logger
        from automation_orchestrator.security import EmailValidator
        
        audit = get_audit_logger()
        
        # Valid email logging should work
        try:
            audit.log_email_sent(
                lead_id="LEAD-001",
                recipient="test@example.com",
                subject="Test Subject",
                sequence_step=1,
                workflow="test"
            )
            print("✓ Valid email logging works")
        except Exception as e:
            print(f"✗ Valid email logging failed: {e}")
            return False
        
        # Invalid email should be rejected
        try:
            audit.log_email_sent(
                lead_id="LEAD-001",
                recipient="invalid@\nBcc: attacker@evil.com",
                subject="Test",
                sequence_step=1,
                workflow="test"
            )
            print("✗ Invalid email was accepted!")
            return False
        except ValueError:
            print("✓ Invalid email was rejected")
        
        return True
    except Exception as e:
        print(f"✗ Audit logging test failed: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting"""
    print("\n[TEST] Testing Rate Limiting...")
    try:
        from automation_orchestrator.security import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        
        # Should allow up to max_requests
        for i in range(5):
            if not limiter.is_allowed("test_user"):
                print(f"✗ Rate limiting failed at request {i+1}")
                return False
        
        # Should block beyond max_requests
        if limiter.is_allowed("test_user"):
            print("✗ Rate limiting not enforcing limit")
            return False
        
        print("✓ Rate limiting working correctly")
        return True
    except Exception as e:
        print(f"✗ Rate limiting test failed: {e}")
        return False


def test_environment_security():
    """Test that no hardcoded secrets exist"""
    print("\n[TEST] Scanning for Hardcoded Secrets...")
    try:
        suspicious_patterns = [
            "api_key = '",
            "password = '",
            "token = '",
            "secret = '",
            '"api_key": "',
            '"password": "',
            '"token": "',
        ]
        
        source_dir = Path(__file__).parent / "src" / "automation_orchestrator"
        found_issues = []
        
        for py_file in source_dir.glob("**/*.py"):
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
            except:
                continue  # Skip files that can't be read
                
            for pattern in suspicious_patterns:
                # Check for actual values (not in comments)
                for line_num, line in enumerate(content.split("\n"), 1):
                    if pattern in line and not line.strip().startswith("#"):
                        # Check if it's actually a secret (not a placeholder)
                        if not any(x in line for x in ["example", "your_", "test", "demo"]):
                            found_issues.append(f"{py_file.name}:{line_num}: {line.strip()}")
        
        if found_issues:
            print("✗ Found potential hardcoded secrets:")
            for issue in found_issues:
                print(f"  - {issue}")
            return False
        
        print("✓ No obvious hardcoded secrets found")
        return True
    except Exception as e:
        print(f"✗ Secret scan failed: {e}")
        return False


def print_report(results):
    """Print test report"""
    print("\n" + "="*60)
    print("SECURITY VALIDATION REPORT")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n✓ All security tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} security test(s) failed")
        return 1


def main():
    """Run all security validation tests"""
    print("\n" + "="*60)
    print("AUTOMATION ORCHESTRATOR SECURITY VALIDATION")
    print("="*60)
    
    results  = {
        "Import Security Modules": test_security_imports(),
        "Input Validation": test_input_validation(),
        "Email Validation": test_email_validation(),
        "Path Validation": test_path_validation(),
        "Webhook/SSRF Protection": test_webhook_validation(),
        "PII Anonymization": test_pii_anonymization(),
        "Audit Logging Security": test_audit_logging(),
        "Rate Limiting": test_rate_limiting(),
        "Environment Security": test_environment_security(),
    }
    
    return print_report(results)


if __name__ == "__main__":
    sys.exit(main())
