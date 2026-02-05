"""
Security utilities for Automation Orchestrator
Provides validators, sanitizers, and security functions
"""

import re
import secrets
import ipaddress
import socket
import html as html_module
from pathlib import Path
from typing import Optional, Set, Dict, Any
from urllib.parse import urlparse
from email.utils import parseaddr
import hashlib
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# ============================================================================
# Input Validation Classes
# ============================================================================

class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Alphanumeric, hyphens, underscores only
    LEAD_ID_REGEX = re.compile(r'^[A-Za-z0-9_-]{1,50}$')
    WORKFLOW_NAME_REGEX = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
    SOURCE_REGEX = re.compile(r'^[A-Za-z0-9_:.-]{1,50}$')
    
    @staticmethod
    def validate_lead_id(lead_id: Optional[str]) -> Optional[str]:
        """Validate lead ID format"""
        if lead_id is None:
            return None
        
        if not isinstance(lead_id, str):
            raise ValueError("Lead ID must be string")
        
        if not InputValidator.LEAD_ID_REGEX.match(lead_id):
            raise ValueError(
                f"Invalid lead ID format. "
                "Must be alphanumeric with hyphens/underscores, max 50 chars"
            )
        
        return lead_id.strip()
    
    @staticmethod
    def validate_workflow_name(workflow: Optional[str]) -> Optional[str]:
        """Validate workflow name"""
        if workflow is None:
            return None
        
        if not isinstance(workflow, str):
            raise ValueError("Workflow name must be string")
        
        if not InputValidator.WORKFLOW_NAME_REGEX.match(workflow):
            raise ValueError(
                f"Invalid workflow name. "
                "Must be alphanumeric with hyphens/underscores, max 100 chars"
            )
        
        return workflow.strip()
    
    @staticmethod
    def validate_source(source: Optional[str]) -> Optional[str]:
        """Validate data source"""
        if source is None:
            return None
        
        if not isinstance(source, str):
            raise ValueError("Source must be string")
        
        if not InputValidator.SOURCE_REGEX.match(source):
            raise ValueError(
                f"Invalid source format. "
                "Must be alphanumeric with colons/dots/hyphens, max 50 chars"
            )
        
        return source.strip()
    
    @staticmethod
    def validate_dict(data: Optional[Dict]) -> Optional[Dict]:
        """Validate dictionary data (prevent injection)"""
        if data is None:
            return None
        
        if not isinstance(data, dict):
            raise ValueError("Data must be dictionary")
        
        # Limit size
        if len(json.dumps(data)) > 10_000_000:  # 10MB max
            raise ValueError("Data too large")
        
        return data


class EmailValidator:
    """Validate email addresses and headers"""
    
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    MAX_EMAIL_LENGTH = 254
    MAX_HEADER_LENGTH = 998
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address format - prevents SMTP injection"""
        if not email or len(email) > EmailValidator.MAX_EMAIL_LENGTH:
            raise ValueError("Invalid email length")
        
        # Check for CRLF injection attempts
        if '\r' in email or '\n' in email:
            raise ValueError("Email contains invalid characters (CRLF)")
        
        # Validate format
        if not EmailValidator.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid email format")
        
        # Additional check using stdlib
        name, addr = parseaddr(email)
        if not addr or addr != email:
            raise ValueError("Email validation failed")
        
        return email.lower()
    
    @staticmethod
    def sanitize_header(text: str, max_length: int = 998) -> str:
        """Sanitize email header text - prevents header injection"""
        if not text:
            return ""
        
        # Remove CRLF
        text = text.replace('\r', '').replace('\n', ' ')
        
        # Limit length
        return text[:max_length]


class PathValidator:
    """Validate file paths - prevents path traversal"""
    
    # Define allowed base directories
    ALLOWED_BASE_DIRS = [
        Path("logs").resolve(),
        Path("reports").resolve(),
        Path("data").resolve(),
        Path("backups").resolve(),
    ]
    
    @classmethod
    def validate_path(cls, file_path: str, base_dir: Optional[Path] = None) -> Path:
        """Validate path is within allowed directories"""
        try:
            path = Path(file_path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path format: {e}")
        
        # Create allowed dirs list
        check_dirs = cls.ALLOWED_BASE_DIRS if base_dir is None else [base_dir.resolve()]
        
        # Check if path is within allowed directories
        for allowed in check_dirs:
            try:
                path.relative_to(allowed)
                return path
            except ValueError:
                continue
        
        raise ValueError(f"Path is outside allowed directories")
    
    @classmethod
    def add_allowed_directory(cls, dir_path: str) -> None:
        """Add directory to allowed list"""
        cls.ALLOWED_BASE_DIRS.append(Path(dir_path).resolve())


class WebhookValidator:
    """Validate webhook URLs - prevents SSRF attacks"""
    
    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Private
        ipaddress.ip_network("172.16.0.0/12"),    # Private
        ipaddress.ip_network("192.168.0.0/16"),   # Private
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local (AWS metadata)
        ipaddress.ip_network("224.0.0.0/4"),      # Multicast
        ipaddress.ip_network("::1/128"),          # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ]
    
    ALLOWED_SCHEMES = ["https"]  # Only HTTPS
    MAX_URL_LENGTH = 2048
    
    @classmethod
    def validate_webhook_url(cls, url: str) -> str:
        """Validate webhook URL is safe - prevents SSRF"""
        if not url or len(url) > cls.MAX_URL_LENGTH:
            raise ValueError("Invalid webhook URL length")
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("Invalid webhook URL format")
        
        # Check scheme
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(f"Webhook scheme must be {cls.ALLOWED_SCHEMES}")
        
        # Check hostname
        if not parsed.hostname:
            raise ValueError("Webhook URL must have hostname")
        
        # Resolve hostname to IP and check against blocked networks
        try:
            ip = socket.gethostbyname(parsed.hostname)
            ip_addr = ipaddress.ip_address(ip)
            
            for network in cls.BLOCKED_NETWORKS:
                if ip_addr in network:
                    raise ValueError(f"Webhook URL resolves to blocked network")
        except socket.gaierror:
            raise ValueError("Cannot resolve webhook hostname")
        except Exception as e:
            raise ValueError(f"Webhook validation failed: {e}")
        
        # Check for suspicious patterns
        suspicious_patterns = [r'@', r'localhost', r'127\.0\.0\.1', r'169\.254', r'metadata']
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("Webhook URL contains suspicious patterns")
        
        return url


# ============================================================================
# Data Protection Classes
# ============================================================================

class SecretManager:
    """Manage secrets securely using environment variables"""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> str:
        """Get secret from environment"""
        import os
        
        value = os.environ.get(key)
        if value:
            return value
        
        if default:
            return default
        
        raise ValueError(f"Secret {key} not found in environment")
    
    @staticmethod
    def get_secret_or_env(key: str, env_var: str, default: Optional[str] = None) -> str:
        """Try key first, then env var, then default"""
        import os
        
        # Try explicit key
        result = os.environ.get(key)
        if result:
            return result
        
        # Try env var
        result = os.environ.get(env_var)
        if result:
            return result
        
        # Use default
        if default:
            return default
        
        raise ValueError(f"Secret {key}/{env_var} not configured")


class PIIManager:
    """Protect personally identifiable information"""
    
    # PII patterns
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CC_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
    
    @staticmethod
    def anonymize_email(email: str, char_count: int = 3) -> str:
        """Anonymize email address"""
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) > char_count:
            local = local[:char_count] + '*' * (len(local) - char_count)
        else:
            local = '*' * len(local)
        
        return f"{local}@{domain}"
    
    @staticmethod
    def anonymize_phone(phone: str) -> str:
        """Anonymize phone number"""
        if len(phone) < 4:
            return phone
        return phone[:-4] + '****'
    
    @staticmethod
    def mask_text(text: str, unmask_chars: int = 3) -> str:
        """Mask text showing only first N characters"""
        if len(text) <= unmask_chars:
            return '*' * len(text)
        return text[:unmask_chars] + '*' * (len(text) - unmask_chars)
    
    @staticmethod
    def redact_dict(data: Dict, pii_keys: Set[str]) -> Dict:
        """Redact PII from dictionary"""
        redacted = data.copy()
        for key in pii_keys:
            if key in redacted:
                value = redacted[key]
                if isinstance(value, str):
                    redacted[key] = PIIManager.mask_text(value)
        return redacted


class SecurityKeyManager:
    """Manage security keys (persisted)"""
    
    def __init__(self, key_file: str = "config/.security_key"):
        self.key_file = Path(key_file)
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_create_key()
    
    def _load_or_create_key(self) -> str:
        """Load existing key or create new one"""
        if self.key_file.exists():
            with open(self.key_file, 'r') as f:
                key = f.read().strip()
                if key and len(key) == 64:
                    return key
        
        # Create new key
        key = secrets.token_hex(32)
        self.key_file.write_text(key)
        self.key_file.chmod(0o600)  # Only owner can read
        
        logger.info(f"Generated new security key: {self.key_file}")
        return key
    
    def get_key(self) -> str:
        """Get current security key"""
        return self._key
    
    def sign(self, data: str) -> str:
        """Sign data using HMAC"""
        import hmac
        signature = hmac.new(
            self._key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify(self, data: str, signature: str) -> bool:
        """Verify data signature"""
        expected_sig = self.sign(data)
        return secrets.compare_digest(expected_sig, signature)


# ============================================================================
# Output Protection
# ============================================================================

class OutputSanitizer:
    """Sanitize output to prevent injection attacks"""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        return html_module.escape(text)
    
    @staticmethod
    def escape_csv(text: str) -> str:
        """Escape CSV values"""
        if ',' in text or '"' in text or '\n' in text:
            return '"' + text.replace('"', '""') + '"'
        return text
    
    @staticmethod
    def escape_json(text: str) -> str:
        """Escape for JSON"""
        return json.dumps(text)
    
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """Sanitize log message to prevent log injection"""
        # Remove CRLF
        message = message.replace('\r', '').replace('\n', ' ')
        # Limit length
        return message[:500]


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple rate limiting mechanism"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        now = datetime.now().timestamp()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Add new request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in current window"""
        if identifier not in self.requests:
            return self.max_requests
        
        now = datetime.now().timestamp()
        valid_requests = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        return max(0, self.max_requests - len(valid_requests))


# ============================================================================
# Security Event Logging
# ============================================================================

class SecurityEventLogger:
    """Log security-related events"""
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger
    
    def log_auth_attempt(self, user_id: str, success: bool, reason: str = ""):
        """Log authentication attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.warning(
            f"AUTH_ATTEMPT status={status} user_id={user_id} reason={reason}"
        )
    
    def log_authorization_failure(self, user_id: str, action: str, resource: str):
        """Log authorization failure"""
        self.logger.warning(
            f"AUTHZ_FAILURE user_id={user_id} action={action} resource={resource}"
        )
    
    def log_input_validation_failure(self, input_type: str, reason: str):
        """Log input validation failure"""
        self.logger.warning(
            f"INPUT_VALIDATION_FAILURE type={input_type} reason={reason}"
        )
    
    def log_suspicious_activity(self, activity_type: str, details: str):
        """Log suspicious activity"""
        self.logger.critical(
            f"SUSPICIOUS_ACTIVITY type={activity_type} details={details}"
        )
    
    def log_config_error(self, error_type: str, detail: str):
        """Log configuration errors"""
        self.logger.critical(
            f"CONFIG_ERROR type={error_type} detail={detail}"
        )


# Create global instances
security_logger = SecurityEventLogger()
rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)
key_manager = SecurityKeyManager()
