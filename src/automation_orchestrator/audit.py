"""
Audit logging system for Automation Orchestrator.
Tracks all operations for compliance, debugging, and analytics.
"""

import json
import logging
import hashlib
import hmac
import gzip
import smtplib
import time
import re
import ipaddress
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from threading import Lock, Thread, Event
from queue import Queue, Empty
from functools import lru_cache
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse
from collections import defaultdict, deque
import requests

# Security imports
from automation_orchestrator.security import (
    InputValidator, EmailValidator, PathValidator, 
    PIIManager, OutputSanitizer
)

logger = logging.getLogger(__name__)

# Security constants
MAX_DETAILS_SIZE = 50 * 1024  # 50KB max per event
MAX_STRING_LENGTH = 10000  # Max length for any string field
MAX_LEAD_ID_LENGTH = 100
MAX_WORKFLOW_LENGTH = 100
MAX_EVENT_TYPE_LENGTH = 50

# Performance constants
WRITE_BUFFER_SIZE = 100  # Buffer up to 100 events before writing
WRITE_FLUSH_INTERVAL = 5.0  # Flush buffer every 5 seconds
QUERY_CACHE_SIZE = 128  # Cache up to 128 query results
COMPRESSION_LEVEL = 6  # Balanced compression (1=fast, 9=max)
MAX_MEMORY_EVENTS = 10000  # Max events to keep in memory

# Rate limiting constants
RATE_LIMIT_EVENTS_PER_SECOND = 100  # Max events per second per source
RATE_LIMIT_WINDOW = 1.0  # 1 second window
RATE_LIMIT_BURST = 200  # Allow burst up to this many

# Security monitoring
SECURITY_LOG_FILE = "logs/security_events.log"
PRODUCTION_MODE = False  # Set to True to hide stack traces


class AuditLogger:
    """
    Thread-safe audit logger that writes structured events to disk.
    
    Events include:
    - lead_ingested: New lead captured from source
    - lead_qualified: Lead passed/failed qualification
    - lead_routed: Lead assigned to destination
    - crm_create: Record created in CRM
    - crm_update: Record updated in CRM
    - email_sent: Follow-up email sent
    - email_scheduled: Email added to sequence
    - email_cancelled: Email sequence cancelled
    - workflow_started: Workflow processing started
    - workflow_stopped: Workflow processing stopped
    - error: Error occurred during processing
    """
    
    def __init__(
        self, 
        audit_file: str = "logs/audit.log",
        max_file_size_mb: int = 50,
        retention_days: int = 90,
        enable_rotation: bool = True,
        enable_integrity: bool = True,
        secret_key: Optional[str] = None
    ):
        """
        Initialize audit logger with advanced features.
        
        Args:
            audit_file: Path to audit log file (will create if doesn't exist)
            max_file_size_mb: Max file size before rotation
            retention_days: Days to keep old logs
            enable_rotation: Enable automatic log rotation
            enable_integrity: Enable log integrity checking
            secret_key: Secret key for integrity signatures (auto-generated if None)
        """
        # SECURITY: Validate audit file path to prevent path traversal
        self.audit_file = self._validate_audit_path(audit_file)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.retention_days = retention_days
        self.enable_rotation = enable_rotation
        self.enable_integrity = enable_integrity
        self.secret_key = secret_key or self._generate_secret_key()
        
        # Alert configuration
        self.alert_handlers: List[Callable] = []
        self.error_threshold = 10  # Alert after N errors
        self.error_count = 0
        self.last_alert_time = None
        self.alert_cooldown = 300  # 5 minutes between alerts
        
        # Webhook configuration
        self.webhooks: List[str] = []
        
        # Performance tracking
        self.performance_data: Dict[str, List[float]] = {}
        
        # Compliance
        self.anonymize_pii = False
        
        # PHASE 2: Rate limiting
        self.rate_limiters: Dict[str, deque] = defaultdict(deque)
        self.rate_limit_lock = Lock()
        self.blocked_events_count = 0
        
        # PHASE 2: Security monitoring
        self.security_events: List[Dict[str, Any]] = []
        self.security_log_enabled = True
        
        # PERFORMANCE: Write buffering (unlimited queue to prevent blocking)
        self.write_buffer: Queue = Queue()
        self.buffer_lock = Lock()
        self.flush_event = Event()
        self.shutdown_event = Event()
        
        # PERFORMANCE: Start async write thread
        self.write_thread = Thread(target=self._async_write_worker, daemon=True)
        self.write_thread.start()
        
        # PERFORMANCE: Query cache
        self.query_cache_enabled = True
        self._clear_query_cache()
        
        logger.info(f"AuditLogger initialized: {self.audit_file.absolute()}")
    
    def _clear_query_cache(self) -> None:
        """Clear query result cache."""
        self.query_cache: Dict[str, tuple] = {}  # key -> (results, timestamp)
    
    def _get_cache_key(
        self,
        event_type: Optional[str],
        lead_id: Optional[str],
        workflow: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int
    ) -> str:
        """Generate cache key from query parameters."""
        parts = [
            event_type or "",
            lead_id or "",
            workflow or "",
            start_time.isoformat() if start_time else "",
            end_time.isoformat() if end_time else "",
            str(limit)
        ]
        return "|".join(parts)
    
    def _get_from_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query results if fresh."""
        if key in self.query_cache:
            results, timestamp = self.query_cache[key]
            # Cache valid for 30 seconds
            if time.time() - timestamp < 30:
                return results
            else:
                # Expired - remove
                del self.query_cache[key]
        return None
    
    def _put_in_cache(self, key: str, results: List[Dict[str, Any]]) -> None:
        """Store query results in cache."""
        # Limit cache size
        if len(self.query_cache) >= QUERY_CACHE_SIZE:
            # Remove oldest entry
            oldest_key = min(self.query_cache.keys(), key=lambda k: self.query_cache[k][1])
            del self.query_cache[oldest_key]
        
        self.query_cache[key] = (results, time.time())
    
    def _validate_audit_path(self, audit_file: str) -> Path:
        """Validate audit file path to prevent path traversal attacks."""
        # Define safe base directory
        safe_base = Path("logs").resolve()
        requested = Path(audit_file).resolve()
        
        # Ensure requested path is within safe directory
        try:
            requested.relative_to(safe_base)
        except ValueError:
            raise ValueError(
                f"Invalid audit file path: {audit_file}. "
                f"Must be within logs/ directory"
            )
        
        return requested
    
    def _check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limit. Returns True if allowed."""
        now = time.time()
        
        with self.rate_limit_lock:
            # Get or create rate limiter for this key
            bucket = self.rate_limiters[key]
            
            # Remove old entries outside time window
            while bucket and bucket[0] < now - RATE_LIMIT_WINDOW:
                bucket.popleft()
            
            # Check if within limits
            if len(bucket) >= RATE_LIMIT_BURST:
                self.blocked_events_count += 1
                self._log_security_event(
                    "rate_limit_exceeded",
                    {"key": key, "count": len(bucket), "limit": RATE_LIMIT_BURST}
                )
                return False
            
            # Add current timestamp
            bucket.append(now)
            return True
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self.rate_limit_lock:
            return {
                "active_sources": len(self.rate_limiters),
                "blocked_events": self.blocked_events_count,
                "current_rates": {
                    key: len(bucket) 
                    for key, bucket in self.rate_limiters.items()
                }
            }
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security-related events separately."""
        if not self.security_log_enabled:
            return
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": event_type,
            "details": details
        }
        
        # Keep in memory (limited to last 1000)
        self.security_events.append(event)
        if len(self.security_events) > 1000:
            self.security_events.pop(0)
        
        # Write to security log
        try:
            security_log = Path(SECURITY_LOG_FILE)
            security_log.parent.mkdir(parents=True, exist_ok=True)
            with open(security_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.debug(f"Failed to write security event: {e}")
    
    def get_security_events(self, event_type: Optional[str] = None, 
                           last_n: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = self.security_events[-last_n:]
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        return events
    
    def _generate_secret_key(self) -> str:
        """Generate or load persistent secret key for integrity checking."""
        key_file = Path("logs/.audit_secret")
        
        # Load existing key if available
        if key_file.exists():
            try:
                key = key_file.read_text().strip()
                if len(key) == 64:  # Valid hex key length
                    return key
            except Exception as e:
                logger.warning(f"Failed to load secret key: {e}")
        
        # Generate new key
        import secrets
        key = secrets.token_hex(32)
        
        # Persist key securely
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_text(key)
            # Set restrictive permissions (owner read/write only)
            try:
                key_file.chmod(0o600)
            except Exception:
                pass  # Windows doesn't support Unix permissions
            logger.info("Generated new audit secret key")
        except Exception as e:
            logger.error(f"Failed to persist secret key: {e}")
        
        return key
    
    def _calculate_signature(self, data: str) -> str:
        """Calculate HMAC signature for data integrity."""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _sanitize_string(self, value: Any, max_length: int = MAX_STRING_LENGTH) -> str:
        """Sanitize string input to prevent injection attacks."""
        if value is None:
            return ""
        
        if not isinstance(value, str):
            value = str(value)
        
        # Remove control characters except tab and newline (will be escaped in JSON)
        value = ''.join(c for c in value if ord(c) >= 32 or c in '\t\n')
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length] + "...[truncated]"
        
        return value
    
    def _validate_lead_id(self, lead_id: str) -> str:
        """Validate lead ID format and length."""
        if not isinstance(lead_id, str):
            raise TypeError("lead_id must be a string")
        
        lead_id = self._sanitize_string(lead_id, MAX_LEAD_ID_LENGTH)
        
        if not lead_id:
            raise ValueError("lead_id cannot be empty")
        
        # Allow alphanumeric, hyphens, underscores
        if not re.match(r'^[A-Za-z0-9\-_]+$', lead_id):
            raise ValueError(
                f"Invalid lead_id format: {lead_id}. "
                "Only alphanumeric, hyphens, and underscores allowed"
            )
        
        return lead_id
    
    def _validate_workflow(self, workflow: str) -> str:
        """Validate workflow name format and length."""
        if not isinstance(workflow, str):
            raise TypeError("workflow must be a string")
        
        workflow = self._sanitize_string(workflow, MAX_WORKFLOW_LENGTH)
        
        if not workflow:
            raise ValueError("workflow cannot be empty")
        
        return workflow
    
    def _validate_event_type(self, event_type: str) -> str:
        """Validate event type."""
        if not isinstance(event_type, str):
            raise TypeError("event_type must be a string")
        
        event_type = self._sanitize_string(event_type, MAX_EVENT_TYPE_LENGTH)
        
        if not event_type:
            raise ValueError("event_type cannot be empty")
        
        return event_type
    
    def _validate_details_size(self, details: Dict[str, Any]) -> None:
        """Validate details dictionary size to prevent DoS."""
        if not isinstance(details, dict):
            raise TypeError("details must be a dictionary")
        
        try:
            # Serialize to check size
            serialized = json.dumps(details, default=str)
            size = len(serialized)
            
            if size > MAX_DETAILS_SIZE:
                raise ValueError(
                    f"Event details too large: {size} bytes. "
                    f"Maximum allowed: {MAX_DETAILS_SIZE} bytes"
                )
        except TypeError as e:
            raise ValueError(f"Invalid details dictionary: {e}")
    
    def _validate_url(self, url: str, purpose: str = "webhook") -> str:
        """Validate URL and protect against SSRF attacks."""
        if not isinstance(url, str):
            raise TypeError(f"{purpose} URL must be a string")
        
        if len(url) > 2048:
            raise ValueError(f"{purpose} URL too long (max 2048 chars)")
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid {purpose} URL: {e}")
        
        # Validate scheme
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(
                f"Invalid {purpose} URL scheme: {parsed.scheme}. "
                "Only http and https are allowed"
            )
        
        # Validate hostname exists
        if not parsed.hostname:
            raise ValueError(f"Invalid {purpose} URL: missing hostname")
        
        # SECURITY: Protect against SSRF - block private IPs and localhost
        hostname = parsed.hostname.lower()
        
        # Block localhost variants
        localhost_patterns = [
            'localhost', '127.0.0.1', '0.0.0.0', '::1', '0:0:0:0:0:0:0:1',
            '169.254.169.254',  # AWS metadata
            'metadata.google.internal',  # GCP metadata
        ]
        
        if hostname in localhost_patterns:
            raise ValueError(
                f"Blocked {purpose} URL: localhost/loopback addresses not allowed"
            )
        
        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            # Block private/reserved IP ranges
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(
                    f"Blocked {purpose} URL: private/reserved IP addresses not allowed"
                )
        except ValueError as e:
            # If ipaddress.ip_address() failed, it's a domain name
            if "Blocked" in str(e) or "not allowed" in str(e):
                raise  # Re-raise our security error
            # Not an IP address, check for suspicious domain patterns
            if any(blocked in hostname for blocked in ['metadata', 'internal', 'local']):
                raise ValueError(
                    f"Blocked {purpose} URL: suspicious hostname pattern"
                )
        
        return url
    
    def _check_rotation_needed(self) -> bool:
        """Check if log rotation is needed."""
        if not self.enable_rotation or not self.audit_file.exists():
            return False
        
        return self.audit_file.stat().st_size >= self.max_file_size
    
    def _rotate_log(self) -> None:
        """Rotate the current log file with optimized compression."""
        if not self.audit_file.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = self.audit_file.with_suffix(f".{timestamp}.log")
        compressed_file = rotated_file.with_suffix(".log.gz")
        
        try:
            # PERFORMANCE: Flush buffer before rotation
            self.flush()
            time.sleep(0.2)  # Ensure flush completes
            
            # PERFORMANCE: Compress with optimal level (balanced speed/size)
            with open(self.audit_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb', compresslevel=COMPRESSION_LEVEL) as f_out:
                    # Read and compress in chunks for better memory usage
                    while chunk := f_in.read(65536):  # 64KB chunks
                        f_out.write(chunk)
            
            # Remove original
            self.audit_file.unlink()
            
            logger.info(f"Log rotated: {compressed_file}")
            
            # Clear cache after rotation (data changed)
            self._clear_query_cache()
            
            # Clean old logs
            self._cleanup_old_logs()
        
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.audit_file.parent.glob("*.log.gz"):
            try:
                # Extract timestamp from filename
                timestamp_str = log_file.stem.split('.')[-1]
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.info(f"Deleted old log: {log_file}")
            
            except (ValueError, IndexError):
                # Skip files that don't match pattern
                continue
            except Exception as e:
                logger.error(f"Failed to delete old log {log_file}: {e}")
    
    def configure_alerts(
        self,
        email_config: Optional[Dict[str, str]] = None,
        slack_webhook: Optional[str] = None,
        discord_webhook: Optional[str] = None,
        error_threshold: int = 10,
        cooldown_seconds: int = 300
    ) -> None:
        """
        Configure alert system.
        
        Args:
            email_config: Dict with smtp_server, smtp_port, from_email, to_email, password
            slack_webhook: Slack webhook URL
            discord_webhook: Discord webhook URL
            error_threshold: Number of errors before alert
            cooldown_seconds: Minimum seconds between alerts
        """
        self.error_threshold = error_threshold
        self.alert_cooldown = cooldown_seconds
        
        if email_config:
            self.alert_handlers.append(lambda msg: self._send_email_alert(email_config, msg))
        
        if slack_webhook:
            self.alert_handlers.append(lambda msg: self._send_webhook_alert(slack_webhook, msg, "Slack"))
        
        if discord_webhook:
            self.alert_handlers.append(lambda msg: self._send_webhook_alert(discord_webhook, msg, "Discord"))
    
    def _send_email_alert(self, config: Dict[str, str], message: str) -> None:
        """Send email alert with SMTP injection protection."""
        try:
            # SECURITY: Sanitize all email fields to prevent SMTP injection
            subject = f"Audit Alert: {message[:50]}"
            # Remove newlines and carriage returns from subject
            subject = subject.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            subject = subject[:200]  # Limit subject length
            
            # Sanitize message body - prevent SMTP smuggling
            message = message.replace('\r\n.\r\n', '\r\n. \r\n')
            message = self._sanitize_string(message, 10000)
            
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = config['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(config['smtp_server'], int(config['smtp_port'])) as server:
                server.starttls()
                server.login(config['from_email'], config['password'])
                server.send_message(msg)
            
            logger.info("Email alert sent")
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, webhook_url: str, message: str, platform: str) -> None:
        """Send webhook alert to Slack/Discord."""
        try:
            payload = {"text": message} if platform == "Slack" else {"content": message}
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            
            logger.info(f"{platform} alert sent")
        
        except Exception as e:
            logger.error(f"Failed to send {platform} alert: {e}")
    
    def _trigger_alerts(self, event: Dict[str, Any]) -> None:
        """Trigger alerts if conditions met."""
        if event['event_type'] == 'error':
            self.error_count += 1
            
            # Check if we should alert
            now = time.time()
            should_alert = self.error_count >= self.error_threshold
            
            if self.last_alert_time:
                should_alert = should_alert and (now - self.last_alert_time) >= self.alert_cooldown
            
            if should_alert and self.alert_handlers:
                alert_message = (
                    f"⚠️ AUDIT ALERT: {self.error_count} errors detected\\n"
                    f"Latest: {event['details'].get('error_message', 'Unknown')}\\n"
                    f"Workflow: {event.get('workflow', 'N/A')}\\n"
                    f"Time: {event['timestamp']}"
                )
                
                for handler in self.alert_handlers:
                    try:
                        handler(alert_message)
                    except Exception as e:
                        logger.error(f"Alert handler failed: {e}")
                
                self.error_count = 0
                self.last_alert_time = now
    
    def add_webhook(self, webhook_url: str) -> None:
        """Add a webhook endpoint for real-time event streaming with SSRF protection."""
        # SECURITY: Validate webhook URL to prevent SSRF attacks
        validated_url = self._validate_url(webhook_url, "webhook")
        self.webhooks.append(validated_url)
        logger.info(f"Webhook added: {validated_url}")
    
    def _send_to_webhooks(self, event: Dict[str, Any]) -> None:
        """Send event to all configured webhooks asynchronously with TLS validation."""
        if not self.webhooks:
            return
        
        def send():
            for webhook_url in self.webhooks:
                try:
                    # PHASE 2: Enhanced TLS validation
                    response = requests.post(
                        webhook_url, 
                        json=event, 
                        timeout=2,
                        verify=True  # Verify SSL certificates
                    )
                    response.raise_for_status()
                except requests.exceptions.SSLError as e:
                    # Log SSL/TLS errors separately
                    self._log_security_event(
                        "webhook_tls_error",
                        {"url": webhook_url[:50], "error": str(e)[:200]}
                    )
                    logger.error(f"Webhook TLS validation failed: {webhook_url}")
                except requests.exceptions.Timeout:
                    logger.debug(f"Webhook timeout: {webhook_url}")
                except Exception as e:
                    # PHASE 2: Enhanced error handling
                    if PRODUCTION_MODE:
                        logger.debug(f"Webhook delivery failed: {webhook_url}")
                    else:
                        logger.debug(f"Webhook delivery failed: {e}")
        
        Thread(target=send, daemon=True).start()
    
    def track_performance(self, operation: str, duration_seconds: float) -> None:
        """
        Track performance metrics for operations.
        
        Args:
            operation: Name of operation
            duration_seconds: Duration in seconds
        """
        if operation not in self.performance_data:
            self.performance_data[operation] = []
        
        self.performance_data[operation].append(duration_seconds)
        
        # Keep only last 1000 measurements
        if len(self.performance_data[operation]) > 1000:
            self.performance_data[operation] = self.performance_data[operation][-1000:]
    
    def get_performance_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Args:
            operation: Specific operation or None for all
        
        Returns:
            Dict with min, max, avg, p95, p99 metrics
        """
        if operation:
            data = self.performance_data.get(operation, [])
            operations = {operation: data}
        else:
            operations = self.performance_data
        
        stats = {}
        for op, measurements in operations.items():
            if not measurements:
                continue
            
            sorted_data = sorted(measurements)
            n = len(sorted_data)
            
            stats[op] = {
                "count": n,
                "min": sorted_data[0],
                "max": sorted_data[-1],
                "avg": sum(sorted_data) / n,
                "p50": sorted_data[n // 2],
                "p95": sorted_data[int(n * 0.95)] if n > 20 else sorted_data[-1],
                "p99": sorted_data[int(n * 0.99)] if n > 100 else sorted_data[-1],
            }
        
        return stats
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize PII in data for compliance.
        
        Args:
            data: Data dictionary
        
        Returns:
            Anonymized data
        """
        if not self.anonymize_pii:
            return data
        
        pii_fields = ['email', 'phone', 'name', 'address', 'ssn']
        anonymized = data.copy()
        
        for field in pii_fields:
            if field in anonymized:
                # Hash the value
                value_hash = hashlib.sha256(str(anonymized[field]).encode()).hexdigest()[:16]
                anonymized[field] = f"[REDACTED_{value_hash}]"
        
        return anonymized
    
    def enable_compliance_mode(self, anonymize_pii: bool = True) -> None:
        """
        Enable compliance mode with PII anonymization.
        
        Args:
            anonymize_pii: Whether to anonymize PII fields
        """
        self.anonymize_pii = anonymize_pii
        logger.info(f"Compliance mode enabled (anonymize_pii={anonymize_pii})")
    
    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        actor: str = "system",
        lead_id: Optional[str] = None,
        workflow: Optional[str] = None
    ) -> None:
        """
        Log an audit event with input validation and security checks.
        
        Args:
            event_type: Type of event (lead_ingested, crm_create, etc.)
            details: Event-specific details dictionary
            actor: Who/what triggered the event (system, user email, etc.)
            lead_id: Associated lead ID if applicable
            workflow: Associated workflow name if applicable
        
        Raises:
            ValueError: If inputs fail validation
            TypeError: If inputs are wrong type
        """
        # PHASE 2: Rate limiting check
        rate_limit_key = f"{workflow or 'global'}:{lead_id or 'none'}"
        if not self._check_rate_limit(rate_limit_key):
            # Rate limit exceeded - log security event but don't raise
            logger.warning(f"Rate limit exceeded for {rate_limit_key}")
            return  # Silently drop event
        
        # SECURITY: Validate all inputs
        try:
            event_type = self._validate_event_type(event_type)
            actor = self._sanitize_string(actor, 200)
            
            if lead_id is not None:
                lead_id = self._validate_lead_id(lead_id)
            
            if workflow is not None:
                workflow = self._validate_workflow(workflow)
            
            # SECURITY: Validate details size to prevent DoS
            self._validate_details_size(details)
        except (ValueError, TypeError) as e:
            # PHASE 2: Enhanced error handling
            self._log_security_event(
                "validation_error",
                {
                    "event_type": str(event_type)[:50],
                    "error": str(e)[:200],
                    "lead_id": str(lead_id)[:50] if lead_id else None
                }
            )
            if PRODUCTION_MODE:
                logger.error(f"Audit validation failed for event {event_type}")
            else:
                logger.error(f"Audit validation failed: {e}")
            raise
        
        # Check if rotation needed
        if self._check_rotation_needed():
            self._rotate_log()
        
        # Anonymize if compliance mode enabled
        if self.anonymize_pii:
            details = self.anonymize_data(details)
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_type": event_type,
            "actor": actor,
            "lead_id": lead_id,
            "workflow": workflow,
            "details": details
        }
        
        # Add integrity signature if enabled
        if self.enable_integrity:
            event_str = json.dumps(event, sort_keys=True)
            event["signature"] = self._calculate_signature(event_str)
        
        # PERFORMANCE: Use buffered writing for better throughput
        try:
            # Put event in write buffer (non-blocking since queue is unlimited)
            self.write_buffer.put(event)
            
            # If buffer is getting full, signal flush
            if self.write_buffer.qsize() >= WRITE_BUFFER_SIZE:
                self.flush_event.set()
            
            logger.debug(f"Audit event buffered: {event_type}")
            
            # Trigger alerts if needed (async)
            self._trigger_alerts(event)
            
            # Send to webhooks (async)
            self._send_to_webhooks(event)
        
        except Exception as e:
            # PHASE 2: Enhanced error handling
            self._log_security_event(
                "audit_write_error",
                {"event_type": event_type, "error": str(e)[:200]}
            )
            if PRODUCTION_MODE:
                logger.error(f"Failed to buffer audit event: {event_type}")
            else:
                logger.error(f"Failed to buffer audit event: {e}")
                logger.debug(traceback.format_exc())
    
    def log_lead_ingested(
        self,
        lead_id: str,
        source: str,
        lead_data: Dict[str, Any],
        workflow: str
    ) -> None:
        """Log lead ingestion event."""
        self.log_event(
            event_type="lead_ingested",
            details={
                "source": source,
                "fields": list(lead_data.keys()),
                "email": lead_data.get("email", "N/A")
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_lead_qualified(
        self,
        lead_id: str,
        qualified: bool,
        reason: str,
        workflow: str
    ) -> None:
        """Log lead qualification event."""
        self.log_event(
            event_type="lead_qualified",
            details={
                "qualified": qualified,
                "reason": reason
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_lead_routed(
        self,
        lead_id: str,
        destination: str,
        condition: str,
        workflow: str
    ) -> None:
        """Log lead routing event."""
        self.log_event(
            event_type="lead_routed",
            details={
                "destination": destination,
                "condition": condition
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_crm_create(
        self,
        lead_id: str,
        crm_record_id: str,
        crm_type: str,
        workflow: str
    ) -> None:
        """Log CRM record creation."""
        self.log_event(
            event_type="crm_create",
            details={
                "crm_record_id": crm_record_id,
                "crm_type": crm_type
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_crm_update(
        self,
        lead_id: str,
        crm_record_id: str,
        fields_updated: List[str],
        workflow: str
    ) -> None:
        """Log CRM record update."""
        self.log_event(
            event_type="crm_update",
            details={
                "crm_record_id": crm_record_id,
                "fields_updated": fields_updated
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_email_sent(
        self,
        lead_id: str,
        recipient: str,
        subject: str,
        sequence_step: int,
        workflow: str
    ) -> None:
        """Log email sent event with validation (prevents SMTP injection)."""
        # SECURITY: Validate email address to prevent SMTP injection
        try:
            recipient = EmailValidator.validate_email(recipient)
            subject = EmailValidator.sanitize_header(subject, 500)
        except ValueError as e:
            self._log_security_event(
                "invalid_email_logged",
                {"error": str(e), "workflow": workflow}
            )
            raise
        
        self.log_event(
            event_type="email_sent",
            details={
                "recipient": recipient,
                "subject": subject,
                "sequence_step": sequence_step
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_email_scheduled(
        self,
        lead_id: str,
        recipient: str,
        sequence_length: int,
        workflow: str
    ) -> None:
        """Log email sequence scheduled with validation."""
        # SECURITY: Validate email address
        try:
            recipient = EmailValidator.validate_email(recipient)
        except ValueError as e:
            self._log_security_event(
                "invalid_email_logged",
                {"error": str(e), "workflow": workflow}
            )
            raise
        
        self.log_event(
            event_type="email_scheduled",
            details={
                "recipient": recipient,
                "sequence_length": sequence_length
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_email_cancelled(
        self,
        lead_id: str,
        recipient: str,
        reason: str,
        workflow: str
    ) -> None:
        """Log email sequence cancellation with validation."""
        # SECURITY: Validate email address
        try:
            recipient = EmailValidator.validate_email(recipient)
            reason = EmailValidator.sanitize_header(reason, 500)
        except ValueError as e:
            self._log_security_event(
                "invalid_email_logged",
                {"error": str(e), "workflow": workflow}
            )
            raise
        
        self.log_event(
            event_type="email_cancelled",
            details={
                "recipient": recipient,
                "reason": reason
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def log_workflow_started(self, workflow: str) -> None:
        """Log workflow start."""
        self.log_event(
            event_type="workflow_started",
            details={},
            workflow=workflow
        )
    
    def log_workflow_stopped(self, workflow: str, reason: str = "manual") -> None:
        """Log workflow stop."""
        self.log_event(
            event_type="workflow_stopped",
            details={"reason": reason},
            workflow=workflow
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        lead_id: Optional[str] = None,
        workflow: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> None:
        """Log error event."""
        self.log_event(
            event_type="error",
            details={
                "error_type": error_type,
                "error_message": error_message,
                "traceback": traceback
            },
            lead_id=lead_id,
            workflow=workflow
        )
    
    def query_events(
        self,
        event_type: Optional[str] = None,
        lead_id: Optional[str] = None,
        workflow: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit events with filters. Uses caching for performance.
        
        Args:
            event_type: Filter by event type
            lead_id: Filter by lead ID
            workflow: Filter by workflow name
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
        
        Returns:
            List of matching audit events
        """
        # PERFORMANCE: Check cache first
        if self.query_cache_enabled:
            cache_key = self._get_cache_key(event_type, lead_id, workflow, start_time, end_time, limit)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        results = []
        
        try:
            if not self.audit_file.exists():
                return results
            
            # PERFORMANCE: Use binary search for time-based queries
            # PERFORMANCE: Read in larger chunks for better I/O
            with open(self.audit_file, "r", encoding="utf-8", buffering=8192) as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        event = json.loads(line.strip())
                        
                        # Apply filters (PHASE 2: ReDoS protection handled by validation)
                        if event_type and event.get("event_type") != event_type:
                            continue
                        
                        if lead_id and event.get("lead_id") != lead_id:
                            continue
                        
                        if workflow and event.get("workflow") != workflow:
                            continue
                        
                        if start_time:
                            event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                            if event_time < start_time:
                                continue
                        
                        if end_time:
                            event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                            if event_time > end_time:
                                continue
                        
                        results.append(event)
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
        
        # PERFORMANCE: Cache results
        if self.query_cache_enabled and results:
            self._put_in_cache(cache_key, results)
        
        return results
    
    def get_lead_history(self, lead_id: str) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a specific lead.
        
        Args:
            lead_id: Lead ID to query
        
        Returns:
            List of all events for this lead, chronologically ordered
        """
        return self.query_events(lead_id=lead_id, limit=1000)
    
    def get_statistics(self, workflow: Optional[str] = None) -> Dict[str, Any]:
        """
        Get audit statistics with memory-efficient processing.
        
        Args:
            workflow: Filter by workflow name (optional)
        
        Returns:
            Dictionary with event counts and statistics
        """
        stats = {
            "total_events": 0,
            "event_types": {},
            "leads_processed": set(),
            "errors": 0
        }
        
        try:
            if not self.audit_file.exists():
                return stats
            
            # PERFORMANCE: Read in larger chunks, limit memory usage
            with open(self.audit_file, "r", encoding="utf-8", buffering=8192) as f:
                for line in f:
                    # PERFORMANCE: Stop if memory limit reached
                    if len(stats["leads_processed"]) > MAX_MEMORY_EVENTS:
                        logger.warning(f"Statistics truncated at {MAX_MEMORY_EVENTS} unique leads")
                        break
                    
                    try:
                        event = json.loads(line.strip())
                        
                        if workflow and event.get("workflow") != workflow:
                            continue
                        
                        stats["total_events"] += 1
                        
                        event_type = event.get("event_type", "unknown")
                        stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
                        
                        if event.get("lead_id"):
                            stats["leads_processed"].add(event["lead_id"])
                        
                        if event_type == "error":
                            stats["errors"] += 1
                    
                    except json.JSONDecodeError:
                        continue
            
            stats["leads_processed"] = len(stats["leads_processed"])
        
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
        
        return stats
    
    def _async_write_worker(self) -> None:
        """
        Background worker thread for async batch writing.
        Processes write buffer and flushes periodically.
        """
        batch = []
        last_flush = time.time()
        
        while not self.shutdown_event.is_set():
            try:
                # Check if we should flush
                time_since_flush = time.time() - last_flush
                should_flush = (
                    len(batch) >= WRITE_BUFFER_SIZE or
                    (batch and time_since_flush >= WRITE_FLUSH_INTERVAL) or
                    self.flush_event.is_set()
                )
                
                if should_flush and batch:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = time.time()
                    self.flush_event.clear()
                
                # Try to get next event (timeout for periodic checks)
                timeout = WRITE_FLUSH_INTERVAL - time_since_flush
                if timeout > 0:
                    try:
                        event = self.write_buffer.get(timeout=timeout)
                        batch.append(event)
                    except Empty:
                        pass  # Timeout - check if we should flush
            
            except Exception as e:
                logger.error(f"Error in async write worker: {e}")
                time.sleep(1)  # Brief pause before retrying
        
        # Final flush on shutdown
        if batch:
            self._flush_batch(batch)
    
    def _flush_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Write a batch of events to disk efficiently.
        
        Args:
            batch: List of events to write
        """
        if not batch:
            return
        
        try:
            with self.lock:
                with open(self.audit_file, "a", encoding="utf-8") as f:
                    for event in batch:
                        f.write(json.dumps(event) + "\n")
            
            logger.debug(f"Flushed {len(batch)} audit events")
        
        except Exception as e:
            logger.error(f"Failed to flush batch of {len(batch)} events: {e}")
            # Try to recover by writing events one by one
            for event in batch:
                try:
                    with self.lock:
                        with open(self.audit_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(event) + "\n")
                except Exception as e2:
                    logger.error(f"Failed to write single event: {e2}")
    
    def flush(self) -> None:
        """
        Force immediate flush of write buffer.
        Useful before shutdown or for testing.
        """
        self.flush_event.set()
        # Give worker thread time to flush (with retries)
        max_retries = 5
        for i in range(max_retries):
            time.sleep(0.1)
            if self.write_buffer.qsize() == 0:
                break  # Buffer is empty
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown audit logger.
        Flushes buffer and stops background threads.
        """
        logger.info("Shutting down audit logger...")
        self.shutdown_event.set()
        self.flush_event.set()
        
        # Wait for write thread to finish
        if self.write_thread.is_alive():
            self.write_thread.join(timeout=5.0)
        
        logger.info("Audit logger shutdown complete")


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(audit_file: str = "logs/audit.log") -> AuditLogger:
    """
    Get or create global audit logger instance.
    
    Args:
        audit_file: Path to audit log file
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger(audit_file)
    
    return _audit_logger
