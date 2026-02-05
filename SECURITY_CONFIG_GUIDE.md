"""
Security Configuration Guide for Automation Orchestrator
This file documents security best practices and configuration requirements
"""

# ============================================================================
# CRITICAL SECURITY REQUIREMENTS
# ============================================================================

## 1. SECRET MANAGEMENT

### Environment Variables (REQUIRED for Production)
Do NOT hardcode credentials in configuration files. Use environment variables:

```bash
# CRM Connectors
export SF_CLIENT_ID="your_client_id"
export SF_CLIENT_SECRET="your_client_secret"  # Keep secret!
export SF_USERNAME="your_username"
export SF_PASSWORD="your_password"  # Keep secret!

export HUBSPOT_API_KEY="your_api_key"  # Keep secret!
export HUBSPOT_ACCESS_TOKEN="your_access_token"  # Keep secret!

# Email Configuration
export SMTP_SERVER="smtp.gmail.com"
export SMTP_USERNAME="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"  # Use app passwords, not main password!

# API Configuration
export API_SECRET_KEY="generate_with_secrets.token_hex(32)"
```

### Load Secrets Using SecretManager
```python
from automation_orchestrator.security import SecretManager

# Get from environment with fallback to safe default
api_key = SecretManager.get_secret("SF_CLIENT_ID", default="dev_key")

# Raise error if not found
api_key = SecretManager.get_secret("SF_CLIENT_ID")
```


## 2. INPUT VALIDATION

### Using Security Validators
```python
from automation_orchestrator.security import (
    InputValidator, EmailValidator, PathValidator
)

# Validate Lead IDs
lead_id = InputValidator.validate_lead_id(user_input)

# Validate Email Addresses (prevents SMTP injection)
email = EmailValidator.validate_email(user_input)

# Sanitize Email Headers (prevents header injection)
subject = EmailValidator.sanitize_header(subject, max_length=500)

# Validate File Paths (prevents path traversal)
file_path = PathValidator.validate_path("logs/audit.log")
```

### Allowed Lead ID Format
- Characters: A-Z, a-z, 0-9, hyphen (-), underscore (_)
- Max Length: 50 characters
- Examples: `LEAD-001`, `web_form_123`, `crm-sync-ABC123`

### Blocked Lead ID Patterns
- Special characters: `<script>`, `../`, `'`, `"`, `;`
- CRLF injection: `\r\n`
- Path traversal: `../../etc/passwd`


## 3. WEBHOOK SECURITY (SSRF Protection)

### Blocked Networks
The following IP ranges and hostnames are automatically blocked:
- 127.0.0.0/8 (loopback)
- 10.0.0.0/8 (private networks)
- 172.16.0.0/12 (private networks)
- 192.168.0.0/16 (private networks)
- 169.254.0.0/16 (AWS metadata)
- localhost, 127.0.0.1, 0.0.0.0
- AWS metadata: 169.254.169.254
- GCP metadata: metadata.google.internal

### Adding Webhooks Safely
```python
from automation_orchestrator.security import WebhookValidator

# Whitelist validation
validator = WebhookValidator()
try:
    url = validator.validate_webhook_url("https://my-service.com/webhook")
    audit_logger.add_webhook(url)
except ValueError as e:
    print(f"Invalid webhook: {e}")
```

### Allowed Schemes
- HTTPS only (HTTP is blocked)
- Must have valid certificate


## 4. EMAIL SECURITY

### Email Validation
```python
from automation_orchestrator.security import EmailValidator

# Validate email against SMTP injection
try:
    email = EmailValidator.validate_email(user_input)
    print(f"Valid: {email}")
except ValueError as e:
    print(f"Invalid: {e}")
```

### Blocked Email Patterns
- CRLF injection: `\r\n` in email or subject
- Header injection: `Bcc:`, `Cc:` in email field
- Multiple recipients in single field

### Safe Email Logging
```python
# ALWAYS validate before logging
email = EmailValidator.validate_email(email)
subject = EmailValidator.sanitize_header(subject)

audit_logger.log_email_sent(
    lead_id=lead_id,
    recipient=email,  # Validated!
    subject=subject,   # Sanitized!
    sequence_step=1,
    workflow="campaign_1"
)
```


## 5. PII PROTECTION

### Anonymize Sensitive Data
```python
from automation_orchestrator.security import PIIManager

# Before logging/exporting:
email = PIIManager.anonymize_email("john.doe@example.com")
# Result: "joh***@example.com"

phone = PIIManager.anonymize_phone("555-123-4567")
# Result: "555-123-****"

name = PIIManager.mask_text("John Doe", unmask_chars=3)
# Result: "Joh***"
```

### Redact Dictionary Fields
```python
data = {
    "lead_id": "LEAD-001",
    "email": "john.doe@example.com",
    "phone": "555-123-4567"
}

pii_keys = {"email", "phone"}
redacted = PIIManager.redact_dict(data, pii_keys)
# Result: {"lead_id": "LEAD-001", "email": "joh***", "phone": "555-****"}
```


## 6. AUTHENTICATION & AUTHORIZATION

### Rate Limiting
```python
from automation_orchestrator.security import RateLimiter

limiter = RateLimiter(max_requests=1000, window_seconds=60)

if limiter.is_allowed(user_id):
    # Process request
    pass
else:
    # Reject - rate limit exceeded
    raise HTTPException(status_code=429, detail="Rate limit exceeded")

# Check remaining
remaining = limiter.get_remaining(user_id)
print(f"Requests remaining: {remaining}")
```

### Security Event Logging
```python
from automation_orchestrator.security import SecurityEventLogger

logger = SecurityEventLogger()

# Log authentication attempts
logger.log_auth_attempt(user_id="user123", success=True)
logger.log_auth_attempt(user_id="user123", success=False, reason="Invalid password")

# Log authorization failures
logger.log_authorization_failure(user_id="user123", action="delete", resource="lead:LEAD-001")

# Log suspicious activity
logger.log_suspicious_activity("path_traversal_attempt", "user tried to access ../../../etc/passwd")
```


## 7. FILE OPERATIONS

### Safe File Path Validation
```python
from automation_orchestrator.security import PathValidator

# Default allowed directories: logs/, reports/, data/, backups/
try:
    path = PathValidator.validate_path("logs/audit.log")
except ValueError as e:
    print(f"Invalid path: {e}")

# Add custom allowed directory
PathValidator.add_allowed_directory("/var/secure_logs")
```


## 8. PRODUCTION CHECKLIST

- [ ] All secrets in environment variables (not in code)
- [ ] SSL/TLS certificates valid and up-to-date
- [ ] Input validation on all user-facing endpoints
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] PII anonymization enabled by default
- [ ] SSRF protection enabled for webhooks
- [ ] Email validation enabled
- [ ] Path traversal protection enabled
- [ ] SMTP injection protection enabled
- [ ] Security events logged separately
- [ ] Old logs rotated and compressed
- [ ] Error messages don't expose internal details
- [ ] Database credentials in environment only
- [ ] API keys rotated regularly
- [ ] Security audit completed
- [ ] Penetration testing completed


## 9. COMPLIANCE

### GDPR Compliance
- PII is anonymized by default
- Data retention limited to 90 days (configurable)
- Audit trail available for all operations
- Right to erasure supported

### CCPA Compliance
- User data protection enabled
- Data minimization enforced
- Transparency in logging

### SOC 2 Compliance
- Access controls implemented
- Audit trails maintained
- Security monitoring enabled
- Incident response planned


## 10. TROUBLESHOOTING

### Issue: "Secret not found in environment"
**Solution:** Set environment variables:
```bash
export SF_CLIENT_ID="your_value"
export SF_CLIENT_SECRET="your_value"
```

### Issue: "Invalid webhook URL - blocked network"
**Solution:** Use public HTTPS endpoints only. Cannot use:
- Localhost (127.0.0.1)
- Private IPs (10.x.x.x, 192.168.x.x)
- AWS metadata service (169.254.169.254)

### Issue: "Email validation failed"
**Solution:** Ensure email format is valid:
- Must contain @ symbol
- Must have domain with TLD
- No special characters or spaces

### Issue: "Path outside allowed directories"
**Solution:** Use one of the allowed base directories:
- logs/
- reports/
- data/
- backups/

Or add custom:
```python
PathValidator.add_allowed_directory("/your/safe/path")
```


## 11. SECURITY UPDATES

Check regularly for security updates:
```bash
pip install --upgrade automation-orchestrator
```

Review security advisories:
- GitHub Security Advisories
- OWASP Top 10
- CWE/CVSS ratings


## Contact

For security issues, report to: security@your-org.com (DO NOT use public issue tracker!)

"""
