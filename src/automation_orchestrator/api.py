"""
REST API for Automation Orchestrator
Provides endpoints for workflow control, lead management, and CRM integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging
import uuid
from pathlib import Path
import time
from collections import defaultdict, deque
import shutil
import gzip
from automation_orchestrator.audit import get_audit_logger
from automation_orchestrator.deduplication import DeduplicationEngine
from automation_orchestrator.rbac import RBACManager, Role, Permission, User
from automation_orchestrator.analytics import Analytics
from automation_orchestrator.multi_tenancy import TenantManager, TenantContext
from automation_orchestrator.monitoring import (
    setup_json_logging, MetricsCollector, AlertManager, PerformanceTracker
)
from automation_orchestrator.auth import (
    JWTHandler, PasswordHasher, APIKeyManager, UserStore, JWT_SECRET,
    global_user_store, LoginRequest, LoginResponse, APIKeyCreateRequest,
    APIKeyResponse
)
from automation_orchestrator.redis_queue import get_queue
from automation_orchestrator.licensing import LicenseManager

logger = logging.getLogger(__name__)
audit = get_audit_logger()


# ============================================================================
# Request/Response Models
# ============================================================================

class LeadData(BaseModel):
    """Lead data model"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "+1-555-123-4567",
                "company": "Acme Corp",
                "source": "web_form"
            }
        }
    )


class LeadResponse(BaseModel):
    """Response for lead operations"""
    id: str
    status: str
    message: str
    crm_id: Optional[str] = None
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class WorkflowTrigger(BaseModel):
    """Trigger a workflow execution"""
    workflow_id: str
    lead_id: Optional[str] = None
    lead_data: Optional[LeadData] = None
    custom_context: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """Response for workflow operations"""
    id: Optional[str] = None
    workflow_id: str
    execution_id: str
    status: str
    message: str
    timestamp: datetime


class CRMConfig(BaseModel):
    """CRM configuration"""
    crm_type: str  # salesforce, hubspot, etc.
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None
    mapping: Optional[Dict[str, str]] = None


class HealthResponse(BaseModel):
    """System health status"""
    status: str
    version: str
    timestamp: datetime
    components: Dict[str, str]


class DeduplicateRequest(BaseModel):
    """Request to deduplicate leads"""
    leads: List[Dict[str, Any]]
    strategy: Optional[str] = "email"  # email, phone, fuzzy


class DeduplicateLeadsRequest(BaseModel):
    """Request to deduplicate leads with optional payload"""
    leads: Optional[List[Dict[str, Any]]] = None
    strategy: Optional[str] = "email"
    dry_run: Optional[bool] = True


class DeduplicateResponse(BaseModel):
    """Response from deduplication"""
    unique_count: int
    duplicates_found: int
    merged_leads: int
    unique_leads: List[Dict[str, Any]]


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    username: str
    role: str
    email: str
    permissions: List[str]


class TenantResponse(BaseModel):
    """Tenant response model"""
    tenant_id: str
    name: str
    plan: str
    active: bool
    features: Dict[str, bool]


class LicenseActivateRequest(BaseModel):
    """License activation request"""
    license_key: str


class BulkLeadsRequest(BaseModel):
    """Bulk lead ingestion request"""
    leads: List[LeadData]


class EmailSendRequest(BaseModel):
    """Send email request"""
    to: str
    subject: str
    body: str
    template: Optional[str] = "default"


class EmailCampaignCreateRequest(BaseModel):
    """Create email campaign request"""
    name: str
    subject: str
    template: str
    recipients: List[str]


class UserCreateRequest(BaseModel):
    """Create user request"""
    username: str
    email: Optional[str] = ""
    role: str


class UserRoleUpdateRequest(BaseModel):
    """Update user role request"""
    role: str


class TenantCreateRequest(BaseModel):
    """Create tenant request"""
    name: str
    email: Optional[str] = ""
    owner_id: Optional[str] = None
    plan: Optional[str] = "starter"


# ============================================================================
# API Factory
# ============================================================================

def create_app(config: Dict[str, Any], lead_ingest=None, crm_connector=None, 
               workflow_runner=None, email_followup=None) -> FastAPI:
    """
    Create and configure FastAPI application
    
    Args:
        config: Application configuration
        lead_ingest: Lead ingestion module
        crm_connector: CRM connector module
        workflow_runner: Workflow runner module
        email_followup: Email follow-up module
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Automation Orchestrator API",
        description="REST API for lead management and workflow automation",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json"
    )
    
    # Store dependencies in app state
    app.state.config = config
    app.state.lead_ingest = lead_ingest
    app.state.crm_connector = crm_connector
    app.state.workflow_runner = workflow_runner
    app.state.email_followup = email_followup
    
    # Initialize new systems
    app.state.dedup = DeduplicationEngine(config.get("deduplication", {}))
    app.state.rbac = RBACManager()
    app.state.analytics = Analytics()
    app.state.tenants = TenantManager()

    # Redis queue (required in production when enabled)
    app.state.redis_queue = get_queue(config.get("redis", {}))

    # Production Monitoring & Logging Setup
    log_cfg = config.get("logging", {})
    log_level = getattr(logging, log_cfg.get("level", "INFO"))
    log_dir = log_cfg.get("directory", "logs")
    setup_json_logging(log_dir=log_dir, level=log_level)
    
    # Initialize monitoring components
    app.state.metrics_collector = MetricsCollector(max_history=1440)
    app.state.alert_manager = AlertManager()
    app.state.performance_tracker = PerformanceTracker()
    
    logger.info("Production monitoring initialized", extra={'extra_fields': {
        'log_level': log_cfg.get("level", "INFO"),
        'log_dir': log_dir
    }})

    # Runtime metrics
    app.state.start_time = time.time()
    app.state.metrics = {
        "requests_total": 0,
        "requests_failed": 0,
        "latency_total_ms": 0.0,
        "latency_max_ms": 0.0
    }

    # Rate limiting
    rate_limit_cfg = config.get("rate_limit", {})
    app.state.rate_limit_enabled = rate_limit_cfg.get("enabled", False)
    app.state.rate_limit_window = rate_limit_cfg.get("window_seconds", 60)
    app.state.rate_limit_max = rate_limit_cfg.get("max_requests", 120)
    app.state.rate_limit_buckets = defaultdict(deque)

    # Auth
    auth_cfg = config.get("auth", {})
    app.state.auth_enabled = auth_cfg.get("enabled", False)
    if app.state.auth_enabled and JWT_SECRET == "change-me-in-production-use-strong-secret":
        logger.warning("JWT_SECRET is using the default value; set a strong secret for production")

    # Licensing
    license_cfg = config.get("license", {})
    app.state.license_manager = LicenseManager(license_cfg)
    if app.state.license_manager.enabled and app.state.license_manager.is_default_secret():
        logger.warning("LICENSE_SECRET is using the default value; set a strong secret for production")
    app.state.license_manager.ensure_trial_started()

    # Monitoring thresholds
    monitor_cfg = config.get("monitoring", {})
    app.state.queue_depth_warn = monitor_cfg.get("queue_depth_warn", 1000)

    def _is_public_path(path: str) -> bool:
        # API endpoints that don't require auth
        public_paths = {
            "/health",
            "/health/detailed",
            "/metrics",
            "/api/status",
            "/api/docs",
            "/api/openapi.json",
            "/openapi.json",
            "/docs",
            "/redoc",
            "/api/auth/login",
            "/api/license/status",
            "/api/license/purchase"
        }
        if path in public_paths:
            return True
        
        # Frontend routes (SPA) - allow all non-API routes for React Router
        # The frontend will handle authentication internally
        if not path.startswith("/api/"):
            return True
            
        return False

    def _authenticate_request(request: Request) -> Optional[User]:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            payload = JWTHandler.verify_token(token)
            if payload:
                user = global_user_store.get_user_by_id(payload.get("user_id"))
                if user:
                    return user

        api_key = request.headers.get("x-api-key")
        if api_key:
            return global_user_store.verify_api_key(api_key)

        return None

    def _check_rate_limit(key: str) -> bool:
        now = time.time()
        bucket = app.state.rate_limit_buckets[key]
        window = app.state.rate_limit_window
        max_requests = app.state.rate_limit_max

        while bucket and bucket[0] < now - window:
            bucket.popleft()

        if len(bucket) >= max_requests:
            return False

        bucket.append(now)
        return True

    @app.middleware("http")
    async def auth_rate_limit_metrics_middleware(request: Request, call_next):
        start = time.time()
        path = request.url.path
        method = request.method
        user = None
        status_code = 500
        error_msg = None

        if app.state.auth_enabled and not _is_public_path(path):
            user = _authenticate_request(request)
            if not user:
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            request.state.user = user

        if not _is_public_path(path):
            license_status = app.state.license_manager.get_status()
            request.state.license_status = license_status
            if not app.state.license_manager.is_request_allowed(path, request.method, license_status):
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": "License required",
                        "status": license_status.status,
                        "trial_expires_at": license_status.trial_expires_at,
                        "purchase_url": license_status.purchase_url
                    }
                )

        if app.state.rate_limit_enabled and not _is_public_path(path):
            key = user.user_id if user else (request.client.host if request.client else "unknown")
            if not _check_rate_limit(key):
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            app.state.metrics["requests_failed"] += 1
            error_msg = str(e)
            # Log the exception
            logger.exception(f"Unhandled exception in {method} {path}", extra={
                'extra_fields': {
                    'path': path,
                    'method': method,
                    'error': error_msg
                }
            })
            raise
        finally:
            duration_ms = (time.time() - start) * 1000.0
            
            # Update legacy metrics
            app.state.metrics["requests_total"] += 1
            app.state.metrics["latency_total_ms"] += duration_ms
            if duration_ms > app.state.metrics["latency_max_ms"]:
                app.state.metrics["latency_max_ms"] = duration_ms
            
            # Record in new metrics collector
            app.state.metrics_collector.record_request(
                endpoint=path,
                method=method,
                status_code=status_code,
                latency_ms=duration_ms,
                error=error_msg
            )
            
            # Log request
            logger.info(f"{method} {path} {status_code}", extra={
                'extra_fields': {
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration_ms': round(duration_ms, 2),
                    'user': user.user_id if user else 'anonymous'
                }
            })

        if status_code >= 400:
            app.state.metrics["requests_failed"] += 1

        return response
    
    # Initialize in-memory lead store for testing/caching
    app.state.leads_cache = {}
    app.state.workflows_cache = {}
    
    # Seed test data for stress testing
    app.state.leads_cache["lead-1"] = {
        "id": "lead-1",
        "first_name": "John",
        "last_name": "Test",
        "email": "john.test@example.com",
        "phone": "+1-555-0001",
        "company": "Test Corp",
        "source": "stress_test",
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    app.state.leads_cache["lead-2"] = {
        "id": "lead-2",
        "first_name": "Jane",
        "last_name": "Demo",
        "email": "jane.demo@example.com",
        "phone": "+1-555-0002",
        "company": "Demo Inc",
        "source": "stress_test",
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    app.state.leads_cache["lead-3"] = {
        "id": "lead-3",
        "first_name": "Bob",
        "last_name": "Sample",
        "email": "bob.sample@example.com",
        "phone": "+1-555-0003",
        "company": "Sample LLC",
        "source": "stress_test",
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    # Seed workflow data
    app.state.workflows_cache["workflow-1"] = {
        "id": "workflow-1",
        "name": "Lead Processing",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "executions": 0
    }
    
    # ========================================================================
    # Health & Status Endpoints
    # ========================================================================
    
    @app.get("/health", response_model=HealthResponse, tags=["Status"])
    async def health_check():
        """Check system health and status"""
        redis_ready = app.state.redis_queue.ping() if app.state.redis_queue else False
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(),
            components={
                "api": "running",
                "audit": "running",
                "redis": "ready" if redis_ready else "unavailable",
                "crm_connector": "ready" if app.state.crm_connector else "not_configured",
                "lead_ingest": "ready" if app.state.lead_ingest else "not_configured",
                "workflow_runner": "running" if hasattr(app.state, 'workflow_runner') and app.state.workflow_runner else "not_configured"
            }
        )
    
    @app.get("/health/detailed", tags=["Status"])
    async def health_detailed():
        """Get detailed health status"""
        # Use cached values to avoid expensive checks
        if not hasattr(app.state, '_health_cache'):
            app.state._health_cache = {}
            app.state._health_timestamp = 0
        
        import time
        now = time.time()
        
        # Refresh cache every 5 seconds
        if now - app.state._health_timestamp > 5:
            redis_ok = app.state.redis_queue.ping() if app.state.redis_queue else False
            queue_depth = app.state.redis_queue.get_queue_depth("default") if app.state.redis_queue else 0
            app.state._health_cache = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "api": "running",
                    "cache": "active",
                    "redis": "ready" if redis_ok else "unavailable",
                    "queue_depth": queue_depth,
                    "leads_cached": len(app.state.leads_cache),
                    "workflows_cached": len(app.state.workflows_cache)
                }
            }
            app.state._health_timestamp = now
        
        return app.state._health_cache
    
    @app.get("/api/status", tags=["Status"])
    async def api_status():
        """Get detailed API status"""
        return {
            "api_version": "1.0.0",
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "leads": "available",
                "workflows": "available",
                "crm": "available",
                "email": "available"
            }
        }
    
    @app.get("/metrics", tags=["Status"])
    async def metrics_endpoint():
        """Get comprehensive system metrics with monitoring data"""
        # Get summary from the MetricsCollector
        summary = app.state.metrics_collector.get_summary()
        
        # Check thresholds and generate alerts
        active_alerts = app.state.alert_manager.check_thresholds(summary)
        
        # Add queue depth metric
        queue_depth = app.state.redis_queue.get_queue_depth("default") if app.state.redis_queue else 0
        if queue_depth >= app.state.queue_depth_warn:
            logger.warning(f"Queue depth high: {queue_depth}")
        
        summary['metrics']['queue_depth'] = queue_depth
        summary['active_alerts'] = active_alerts
        summary['rate_limit'] = {
            'enabled': app.state.rate_limit_enabled,
            'window_seconds': app.state.rate_limit_window,
            'max_requests': app.state.rate_limit_max
        }
        
        return summary
    
    @app.get("/api/monitoring/alerts", tags=["Monitoring"])
    async def get_active_alerts():
        """Get active system alerts"""
        summary = app.state.metrics_collector.get_summary()
        alerts = app.state.alert_manager.check_thresholds(summary)
        
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'alert_count': len(alerts),
            'alerts': alerts
        }
    
    @app.get("/api/monitoring/performance", tags=["Monitoring"])
    async def get_performance_metrics():
        """Get detailed performance metrics by operation"""
        stats = {}
        for op_name in app.state.performance_tracker.operations.keys():
            stats[op_name] = app.state.performance_tracker.get_operation_stats(op_name)
        
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'operations': stats
        }
    
    @app.post("/api/monitoring/alerts/threshold", tags=["Monitoring"])
    async def update_alert_threshold(alert_type: str, threshold: float):
        """Update alert threshold"""
        app.state.alert_manager.set_threshold(alert_type, threshold)
        
        logger.info(f"Alert threshold updated: {alert_type} = {threshold}", extra={
            'extra_fields': {
                'alert_type': alert_type,
                'new_threshold': threshold
            }
        })
        
        return {
            'status': 'success',
            'alert_type': alert_type,
            'threshold': threshold
        }
    
    @app.post("/api/monitoring/metrics/export", tags=["Monitoring"])
    async def export_metrics(output_dir: str = "metrics"):
        """Export current metrics to JSON file"""
        filepath = app.state.metrics_collector.export_daily_summary(output_dir)
        
        return {
            'status': 'success',
            'filepath': filepath,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

    
    # ========================================================================
    # Authentication Endpoints
    # ========================================================================
    
    @app.post("/api/auth/login", response_model=LoginResponse, tags=["Authentication"])
    async def login(request: LoginRequest):
        """Authenticate user and return JWT token"""
        user = global_user_store.get_user_by_username(request.username)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # For demo: accept 'admin123' for admin user
        if request.username == "admin" and request.password == "admin123":
            token = JWTHandler.create_token(user.user_id, user.username, user.role)
            global_user_store.update_last_login(user.user_id)
            return LoginResponse(
                access_token=token,
                user_id=user.user_id,
                username=user.username,
                role=user.role,
                expires_in=JWTHandler.get_token_expiration_hours() * 3600
            )
        
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    @app.get("/api/auth/me", tags=["Authentication"])
    async def get_current_user(authorization: str = Header(None)):
        """Get current authenticated user"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        payload = JWTHandler.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user = global_user_store.get_user_by_id(payload["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions
        }
    
    @app.post("/api/auth/keys", response_model=APIKeyResponse, tags=["Authentication"])
    async def create_api_key(
        request: APIKeyCreateRequest,
        authorization: str = Header(None)
    ):
        """Create API key for current user"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        payload = JWTHandler.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        api_key, key_id = global_user_store.create_api_key(
            payload["user_id"],
            request.name,
            request.expires_in_days
        )
        
        return APIKeyResponse(
            key_id=key_id,
            api_key=api_key,
            name=request.name,
            created_at=datetime.now()
        )
    
    @app.get("/api/auth/keys", tags=["Authentication"])
    async def list_api_keys(authorization: str = Header(None)):
        """List API keys for current user"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        payload = JWTHandler.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return global_user_store.list_api_keys(payload["user_id"])
    
    @app.delete("/api/auth/keys/{key_id}", tags=["Authentication"])
    async def revoke_api_key(
        key_id: str,
        authorization: str = Header(None)
    ):
        """Revoke API key"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        payload = JWTHandler.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        if global_user_store.revoke_api_key(key_id):
            return {"message": "API key revoked"}
        
        raise HTTPException(status_code=404, detail="API key not found")

    # ========================================================================
    # Admin & Maintenance Endpoints
    # ========================================================================

    def _require_admin(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

    # ========================================================================
    # Licensing Endpoints
    # ========================================================================

    @app.get("/api/license/status", tags=["License"])
    async def license_status():
        """Get current license status."""
        return app.state.license_manager.get_status().to_dict()

    @app.get("/api/license/purchase", tags=["License"])
    async def license_purchase():
        """Get purchase URL for license."""
        status = app.state.license_manager.get_status()
        return {"purchase_url": status.purchase_url}

    @app.post("/api/license/activate", tags=["License"])
    async def license_activate(request: Request, payload: LicenseActivateRequest):
        """Activate a license key (admin only)."""
        if app.state.auth_enabled:
            _require_admin(request)
        return app.state.license_manager.activate_license(payload.license_key)

    def _create_audit_backup(compress: bool = True) -> Dict[str, Any]:
        audit_file = Path("logs/audit.log")
        backups_dir = Path("backups/audit")
        backups_dir.mkdir(parents=True, exist_ok=True)

        if not audit_file.exists():
            raise HTTPException(status_code=404, detail="Audit log not found")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"audit_backup_{timestamp}.log"
        if compress:
            backup_name += ".gz"

        backup_path = backups_dir / backup_name

        if compress:
            with open(audit_file, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(audit_file, backup_path)

        size_bytes = backup_path.stat().st_size
        return {
            "backup_file": str(backup_path),
            "size_bytes": size_bytes,
            "compressed": compress,
            "created_at": datetime.now().isoformat()
        }

    @app.post("/api/admin/audit/backup", tags=["Admin"])
    async def create_audit_backup(request: Request, compress: bool = True):
        """Create a backup of the audit log (admin only)."""
        _require_admin(request)
        return _create_audit_backup(compress=compress)

    @app.get("/api/admin/audit/backups", tags=["Admin"])
    async def list_audit_backups(request: Request):
        """List audit log backups (admin only)."""
        _require_admin(request)
        backups_dir = Path("backups/audit")
        backups = []
        if backups_dir.exists():
            for backup_file in sorted(backups_dir.glob("audit_backup_*.log*")):
                if backup_file.suffix == ".meta":
                    continue
                backups.append({
                    "backup_file": str(backup_file),
                    "size_bytes": backup_file.stat().st_size,
                    "created_at": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                })
        return {"backups": backups}
    
    # ========================================================================
    # Lead Endpoints
    # ========================================================================
    
    @app.post("/api/leads", response_model=LeadResponse, tags=["Leads"])
    async def create_lead(lead: LeadData, background_tasks: BackgroundTasks):
        """
        Create a new lead
        
        Args:
            lead: Lead data
        
        Returns:
            LeadResponse with created lead info
        """
        try:
            lead_id = str(uuid.uuid4())
            
            # Create lead data object
            lead_dict = {
                "id": lead_id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.company,
                "source": lead.source or "api",
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Store in memory cache immediately (fast path)
            app.state.leads_cache[lead_id] = lead_dict
            
            # Log audit event
            audit.log_event(
                event_type="lead_ingested",
                lead_id=lead_id,
                details={"email": lead.email, "company": lead.company, "source": "api"}
            )
            
            # Async CRM operations (non-blocking)
            if app.state.crm_connector:
                lead_dict['id'] = lead_id
                background_tasks.add_task(
                    app.state.crm_connector.create_or_update_lead,
                    lead_dict
                )
            
            # Trigger workflow if configured
            if app.state.workflow_runner:
                background_tasks.add_task(
                    app.state.workflow_runner.process_lead,
                    lead_id=lead_id,
                    lead_data=lead.dict()
                )
            
            return LeadResponse(
                id=lead_id,
                status="success",
                message="Lead created successfully",
                crm_id=None,
                timestamp=datetime.now(),
                data=lead.dict()
            )
        
        except Exception as e:
            logger.error(f"Error creating lead: {e}", exc_info=True)
            audit.log_event(
                event_type="error",
                details={"error": str(e), "operation": "create_lead"}
            )
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/leads/bulk", tags=["Leads"])
    async def bulk_lead_ingest(request: BulkLeadsRequest, background_tasks: BackgroundTasks):
        """Bulk ingest leads"""
        processed = 0
        lead_ids: List[str] = []
        for lead in request.leads:
            lead_id = str(uuid.uuid4())
            lead_dict = {
                "id": lead_id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.company,
                "source": lead.source or "api",
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            app.state.leads_cache[lead_id] = lead_dict
            lead_ids.append(lead_id)
            processed += 1
            if app.state.crm_connector:
                background_tasks.add_task(
                    app.state.crm_connector.create_or_update_lead,
                    lead_dict
                )
        return {"status": "success", "processed": processed, "lead_ids": lead_ids}
    
    @app.get("/api/leads/{lead_id}", response_model=Dict[str, Any], tags=["Leads"])
    async def get_lead(lead_id: str):
        """
        Get lead details
        
        Args:
            lead_id: Lead ID
        
        Returns:
            Lead data
        """
        try:
            # Check in-memory cache first (fast path)
            if lead_id in app.state.leads_cache:
                return app.state.leads_cache[lead_id]
            
            # Fall back to CRM connector
            if app.state.crm_connector:
                lead = app.state.crm_connector.get_lead(lead_id)
                if lead:
                    # Cache result
                    app.state.leads_cache[lead_id] = lead
                    return lead
            
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching lead: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/leads", response_model=Dict[str, Any], tags=["Leads"])
    async def list_leads(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        source: Optional[str] = None,
        email: Optional[str] = None
    ):
        """
        List leads with filtering
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            source: Filter by lead source
            email: Filter by email
        
        Returns:
            List of leads
        """
        try:
            # Get leads from cache
            leads_list = list(app.state.leads_cache.values())
            
            # Apply filters
            if source:
                leads_list = [l for l in leads_list if l.get('source') == source]
            if email:
                leads_list = [l for l in leads_list if l.get('email') == email]
            
            total = len(leads_list)
            
            # Apply pagination
            leads_page = leads_list[skip:skip + limit]
            
            return {
                "total": total,
                "skip": skip,
                "limit": limit,
                "leads": leads_page
            }
        
        except Exception as e:
            logger.error(f"Error listing leads: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.put("/api/leads/{lead_id}", response_model=LeadResponse, tags=["Leads"])
    async def update_lead(lead_id: str, lead: LeadData, background_tasks: BackgroundTasks):
        """
        Update a lead
        
        Args:
            lead_id: Lead ID
            lead: Updated lead data
        
        Returns:
            Updated lead info
        """
        try:
            # Get existing lead from cache or create new entry
            existing_lead = app.state.leads_cache.get(lead_id, {})
            
            # Update in cache immediately (fast path)
            lead_dict = {
                "id": lead_id,
                "first_name": lead.first_name or existing_lead.get("first_name", ""),
                "last_name": lead.last_name or existing_lead.get("last_name", ""),
                "email": lead.email or existing_lead.get("email", ""),
                "phone": lead.phone or existing_lead.get("phone", ""),
                "company": lead.company or existing_lead.get("company", ""),
                "source": lead.source or existing_lead.get("source", "api"),
                "created_at": existing_lead.get("created_at", datetime.now().isoformat()),
                "status": "active"
            }
            
            # Store in cache
            app.state.leads_cache[lead_id] = lead_dict
            
            # Async CRM update (non-blocking)
            if app.state.crm_connector:
                background_tasks.add_task(
                    app.state.crm_connector.create_or_update_lead,
                    lead_dict
                )
            
            # Build updated fields dict for audit
            updated_fields = {}
            if lead.first_name:
                updated_fields["first_name"] = lead.first_name
            if lead.last_name:
                updated_fields["last_name"] = lead.last_name
            if lead.email:
                updated_fields["email"] = lead.email
            if lead.phone:
                updated_fields["phone"] = lead.phone
            if lead.company:
                updated_fields["company"] = lead.company
                
            audit.log_event(
                event_type="crm_update",
                lead_id=lead_id,
                details={"updated_fields": list(updated_fields.keys())}
            )
            
            return LeadResponse(
                id=lead_id,
                status="updated",
                message="Lead updated successfully",
                timestamp=datetime.now(),
                data=lead.dict()
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating lead: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/leads/bulk", tags=["Leads"])
    async def bulk_lead_ingest(request: BulkLeadsRequest, background_tasks: BackgroundTasks):
        """Bulk ingest leads"""
        processed = 0
        lead_ids: List[str] = []
        for lead in request.leads:
            lead_id = str(uuid.uuid4())
            lead_dict = {
                "id": lead_id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.company,
                "source": lead.source or "api",
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            app.state.leads_cache[lead_id] = lead_dict
            lead_ids.append(lead_id)
            processed += 1
            if app.state.crm_connector:
                background_tasks.add_task(app.state.crm_connector.create_or_update_lead, lead_dict)
        return {"status": "success", "processed": processed, "lead_ids": lead_ids}

    @app.delete("/api/leads/{lead_id}", tags=["Leads"])
    async def delete_lead(lead_id: str):
        """Delete a lead"""
        if lead_id in app.state.leads_cache:
            del app.state.leads_cache[lead_id]
            return {"status": "deleted", "lead_id": lead_id}
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # ========================================================================
    # Workflow Endpoints
    # ========================================================================
    
    @app.post("/api/workflows/trigger", response_model=WorkflowResponse, tags=["Workflows"])
    async def trigger_workflow(trigger: WorkflowTrigger, background_tasks: BackgroundTasks):
        """
        Manually trigger a workflow
        
        Args:
            trigger: Workflow trigger data
        
        Returns:
            Workflow execution info
        """
        try:
            execution_id = str(uuid.uuid4())

            # Record in cache for test and fallback mode
            app.state.workflows_cache[execution_id] = {
                "id": execution_id,
                "workflow_id": trigger.workflow_id,
                "status": "triggered",
                "created_at": datetime.now().isoformat()
            }
            
            audit.log_event(
                event_type="workflow_started",
                details={
                    "execution_id": execution_id,
                    "workflow_id": trigger.workflow_id
                }
            )
            
            # Execute workflow in background if configured
            if app.state.workflow_runner:
                background_tasks.add_task(
                    app.state.workflow_runner.execute_workflow,
                    workflow_id=trigger.workflow_id,
                    execution_id=execution_id,
                    lead_data=trigger.lead_data,
                    context=trigger.custom_context
                )
            
            return WorkflowResponse(
                id=execution_id,
                workflow_id=trigger.workflow_id,
                execution_id=execution_id,
                status="triggered",
                message="Workflow execution started",
                timestamp=datetime.now()
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error triggering workflow: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/workflows/{workflow_id}/status", tags=["Workflows"])
    async def get_workflow_status(workflow_id: str):
        """Get workflow execution status"""
        try:
            if app.state.workflow_runner:
                status = app.state.workflow_runner.get_status(workflow_id)
                return {"workflow_id": workflow_id, "status": status}

            cached = app.state.workflows_cache.get(workflow_id)
            if cached:
                return {"workflow_id": workflow_id, "status": cached.get("status", "unknown")}
            raise HTTPException(status_code=404, detail="Workflow not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching workflow status: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/webhook", tags=["Campaigns"])
    async def campaign_webhook():
        """Campaign webhook endpoint"""
        return {"status": "received", "timestamp": datetime.now().isoformat()}
    
    @app.get("/api/campaigns", tags=["Campaigns"])
    async def list_campaigns():
        """Get all campaigns"""
        return {
            "total": 0,
            "campaigns": [],
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/api/campaigns/{campaign_id}/metrics", tags=["Campaigns"])
    async def get_campaign_metrics(campaign_id: str):
        """Get campaign metrics"""
        return {
            "campaign_id": campaign_id,
            "metrics": {
                "sent": 0,
                "opened": 0,
                "clicked": 0,
                "bounced": 0
            },
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/workflows/active", tags=["Workflows"])
    async def list_active_workflows():
        """List active workflows"""
        workflows = list(app.state.workflows_cache.values())
        return {"total": len(workflows), "workflows": workflows}
    
    # ========================================================================
    # Campaign Endpoints (Continued)
    # ========================================================================

    @app.post("/api/crm/salesforce/sync", tags=["CRM"])
    async def salesforce_sync(payload: Dict[str, Any]):
        """Sync lead to Salesforce"""
        if not app.state.crm_connector:
            return {"status": "not_configured", "message": "No CRM connector configured"}
        try:
            result = app.state.crm_connector.sync_to_salesforce(payload)
            return {"status": "success", "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/crm/salesforce/lead/{sf_lead_id}", tags=["CRM"])
    async def get_salesforce_lead(sf_lead_id: str):
        """Get Salesforce lead"""
        if not app.state.crm_connector:
            raise HTTPException(status_code=404, detail="CRM connector not configured")
        lead = app.state.crm_connector.get_salesforce_lead(sf_lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead

    @app.post("/api/crm/hubspot/sync", tags=["CRM"])
    async def hubspot_sync(payload: Dict[str, Any]):
        """Sync lead to HubSpot"""
        if not app.state.crm_connector:
            return {"status": "not_configured", "message": "No CRM connector configured"}
        try:
            result = app.state.crm_connector.sync_to_hubspot(payload)
            return {"status": "success", "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/crm/hubspot/contact/{contact_id}", tags=["CRM"])
    async def get_hubspot_contact(contact_id: str):
        """Get HubSpot contact"""
        if not app.state.crm_connector:
            raise HTTPException(status_code=404, detail="CRM connector not configured")
        contact = app.state.crm_connector.get_hubspot_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
    
    @app.post("/api/crm/config", tags=["CRM"])
    async def configure_crm(config: CRMConfig):
        """
        Configure CRM connection
        
        Args:
            config: CRM configuration
        
        Returns:
            Configuration result
        """
        try:
            # Validate CRM type
            valid_crms = ['salesforce', 'hubspot', 'generic', 'dynamics', 'zoho']
            if config.crm_type not in valid_crms:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid CRM type. Must be one of: {', '.join(valid_crms)}"
                )
            
            # Store config (would normally save to database)
            app.state.config['crm'] = config.dict()
            
            audit.log_event(
                event_type="crm_configured",
                details={"crm_type": config.crm_type}
            )
            
            return {
                "status": "configured",
                "crm_type": config.crm_type,
                "message": "CRM configuration updated"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error configuring CRM: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/crm/status", tags=["CRM"])
    async def check_crm_status():
        """Check CRM connection status"""
        try:
            if not app.state.crm_connector:
                return {
                    "status": "not_configured",
                    "message": "No CRM connector configured"
                }
            
            # Test connection
            test_result = app.state.crm_connector.test_connection()
            
            return {
                "status": "connected" if test_result else "error",
                "connector_type": app.state.crm_connector.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error checking CRM status: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # Email Endpoints
    # ========================================================================
    
    @app.post("/api/email/send", tags=["Email"])
    async def send_email(request: EmailSendRequest, background_tasks: BackgroundTasks = None):
        """
        Send email to lead
        
        Args:
            lead_id: Target lead ID
            template_id: Email template ID
            custom_subject: Custom subject line
        
        Returns:
            Email send result
        """
        try:
            if not app.state.email_followup:
                raise HTTPException(status_code=500, detail="Email module not configured")
            
            execution_id = str(uuid.uuid4())
            
            if background_tasks:
                background_tasks.add_task(
                    app.state.email_followup.send_email,
                    lead_id=request.to,
                    template_id=request.template or "default",
                    subject=request.subject,
                    execution_id=execution_id
                )
            
            audit.log_event(
                event_type="email_sent",
                lead_id=request.to,
                details={"template_id": request.template}
            )
            
            return {
                "status": "sent",
                "execution_id": execution_id,
                "lead_id": request.to,
                "timestamp": datetime.now().isoformat()
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/email/campaign", tags=["Email"])
    async def create_campaign(request: EmailCampaignCreateRequest):
        """Create an email campaign"""
        campaign_id = str(uuid.uuid4())
        return {
            "campaign_id": campaign_id,
            "status": "created",
            "name": request.name,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/email/templates", tags=["Email"])
    async def list_email_templates():
        """List email templates"""
        return [{"id": "default", "name": "Default"}]

    @app.get("/api/email/campaign/{campaign_id}/stats", tags=["Email"])
    async def get_campaign_stats(campaign_id: str):
        """Get campaign stats"""
        return {
            "campaign_id": campaign_id,
            "sent": 0,
            "opened": 0,
            "clicked": 0
        }
    
    # ========================================================================
    # Deduplication Endpoints
    # ========================================================================
    
    @app.post("/api/dedup", tags=["Deduplication"])
    async def deduplicate_leads(request: DeduplicateRequest):
        """
        Deduplicate a batch of leads
        
        Args:
            request: Deduplication request with leads
        
        Returns:
            Deduplication results
        """
        try:
            result = app.state.dedup.deduplicate_batch(request.leads)
            
            # Track analytics
            app.state.analytics.track_event(
                app.state.analytics.LEAD_CREATED,
                {"count": len(result["unique_leads"])}
            )
            
            return {
                "status": "completed",
                "unique_count": result["merge_summary"]["final_count"],
                "duplicates_found": result["merge_summary"]["duplicates_groups"],
                "merged_leads": result["merge_summary"]["total_merged"],
                "unique_leads": result["unique_leads"]
            }
        
        except Exception as e:
            logger.error(f"Error deduplicating leads: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/leads/deduplicate", tags=["Leads"])
    async def deduplicate_leads_alias(request: DeduplicateLeadsRequest):
        """Deduplicate leads using cached leads when payload is missing"""
        leads = request.leads
        if not leads:
            leads = list(app.state.leads_cache.values())

        result = app.state.dedup.deduplicate_batch(leads)
        merge_summary = result.get("merge_summary", {})
        return {
            "status": "completed",
            "unique_count": merge_summary.get("final_count", len(result.get("unique_leads", []))),
            "duplicates_found": merge_summary.get("duplicates_groups", result.get("duplicates_found", 0)),
            "merged_leads": merge_summary.get("total_merged", 0),
            "unique_leads": result["unique_leads"]
        }
    
    @app.get("/api/dedup/config", tags=["Deduplication"])
    async def get_dedup_config():
        """Get deduplication configuration"""
        return app.state.dedup.get_stats()
    
    # ========================================================================
    # Analytics Endpoints
    # ========================================================================
    
    @app.get("/api/analytics/dashboard", tags=["Analytics"])
    async def analytics_dashboard(days: int = Query(30, ge=1, le=365)):
        """Get analytics dashboard summary"""
        summary = app.state.analytics.get_dashboard_summary(days)
        leads = summary.get("leads", {})
        workflows = summary.get("workflows", {})
        return {
            "total_leads": leads.get("total_leads_created", 0),
            "qualification_rate": leads.get("qualification_rate", 0),
            "active_workflows": workflows.get("total_executions", 0),
            "summary": summary
        }
    
    @app.get("/api/analytics/leads", tags=["Analytics"])
    async def analytics_leads(days: int = Query(30, ge=1, le=365)):
        """Get lead metrics"""
        return app.state.analytics.get_lead_metrics(days)
    
    @app.get("/api/analytics/workflows", tags=["Analytics"])
    async def analytics_workflows(days: int = Query(30, ge=1, le=365)):
        """Get workflow metrics"""
        return app.state.analytics.get_workflow_metrics(days)
    
    @app.get("/api/analytics/emails", tags=["Analytics"])
    async def analytics_emails(days: int = Query(30, ge=1, le=365)):
        """Get email metrics"""
        return app.state.analytics.get_email_metrics(days)
    
    @app.get("/api/analytics/roi", tags=["Analytics"])
    async def analytics_roi(lead_value: float = 100, conversion_rate: float = 0.1):
        """Get ROI estimate"""
        return app.state.analytics.get_roi_estimate(lead_value, conversion_rate)
    
    @app.get("/api/analytics/daily", tags=["Analytics"])
    async def analytics_daily(days: int = Query(30, ge=1, le=365)):
        """Get daily breakdown"""
        return app.state.analytics.get_daily_breakdown(days)
    
    @app.get("/api/analytics/export", tags=["Analytics"])
    async def analytics_export(format: str = Query("json", pattern="^(json|csv)$")):
        """Export analytics data"""
        return {
            "format": format,
            "data": app.state.analytics.export_metrics(format)
        }

    # ========================================================================
    # Audit Endpoints
    # ========================================================================

    def _read_audit_events(limit: int = 50) -> List[Dict[str, Any]]:
        audit_path = Path("logs/audit.log")
        if not audit_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with open(audit_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        return events[-limit:]

    @app.get("/api/audit/events", tags=["Audit"])
    async def list_audit_events(limit: int = Query(50, ge=1, le=500)):
        """List audit events"""
        return _read_audit_events(limit=limit)

    @app.get("/api/audit/events/{event_id}", tags=["Audit"])
    async def get_audit_event(event_id: str):
        """Get audit event detail"""
        events = _read_audit_events(limit=200)
        for event in events:
            if event.get("event_id") == event_id:
                return event
        raise HTTPException(status_code=404, detail="Audit event not found")
    
    # ========================================================================
    # RBAC Endpoints
    # ========================================================================
    
    @app.post("/api/users", tags=["RBAC"])
    async def create_user(request: UserCreateRequest):
        """Create a new user"""
        try:
            role_name = request.role.upper()
            if role_name == "VIEWER":
                role_name = "GUEST"
            user = app.state.rbac.create_user(
                str(uuid.uuid4()),
                request.username,
                Role[role_name],
                request.email or ""
            )
            return user.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/users", tags=["RBAC"])
    async def list_users(active_only: bool = False):
        """List all users"""
        return app.state.rbac.list_users(active_only)
    
    @app.get("/api/users/{user_id}", tags=["RBAC"])
    async def get_user(user_id: str):
        """Get user details"""
        user = app.state.rbac.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.to_dict()
    
    @app.put("/api/users/{user_id}/role", tags=["RBAC"])
    async def update_user_role(user_id: str, request: UserRoleUpdateRequest):
        """Update user role"""
        try:
            role_name = request.role.upper()
            if role_name == "VIEWER":
                role_name = "GUEST"
            success = app.state.rbac.update_user_role(user_id, Role[role_name])
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            return {"status": "updated", "role": request.role}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/users/{user_id}/deactivate", tags=["RBAC"])
    async def deactivate_user(user_id: str):
        """Deactivate user"""
        success = app.state.rbac.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "deactivated"}
    
    @app.post("/api/users/{user_id}/activate", tags=["RBAC"])
    async def activate_user(user_id: str):
        """Activate user"""
        success = app.state.rbac.activate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "activated"}
    
    # ========================================================================
    # Multi-Tenancy Endpoints
    # ========================================================================
    
    @app.post("/api/tenants", tags=["Tenants"])
    async def create_tenant(request: TenantCreateRequest):
        """Create a new tenant"""
        try:
            owner_id = request.owner_id or request.email or "system"
            tenant = app.state.tenants.create_tenant(request.name, owner_id, request.plan or "starter")
            return tenant.to_dict()
        except Exception as e:
            logger.error(f"Error creating tenant: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/tenants", tags=["Tenants"])
    async def list_tenants(active_only: bool = False):
        """List all tenants"""
        return app.state.tenants.list_tenants(active_only)
    
    @app.get("/api/tenants/{tenant_id}", tags=["Tenants"])
    async def get_tenant(tenant_id: str):
        """Get tenant details"""
        tenant = app.state.tenants.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant.to_dict()
    
    @app.put("/api/tenants/{tenant_id}/plan", tags=["Tenants"])
    async def update_tenant_plan(tenant_id: str, plan: str):
        """Update tenant plan"""
        success = app.state.tenants.update_tenant_plan(tenant_id, plan)
        if not success:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return {"status": "updated", "plan": plan}
    
    # ========================================================================
    # Workflow Builder API
    # ========================================================================
    
    @app.get("/api/builder/templates", tags=["Workflows"])
    async def get_workflow_templates():
        """Get pre-built workflow templates"""
        return {
            "templates": [
                {
                    "id": "welcome_email",
                    "name": "Welcome Email",
                    "description": "Send welcome email to new leads",
                    "steps": [
                        {"type": "trigger", "label": "New Lead Created", "config": {"type": "new_lead"}},
                        {"type": "action", "label": "Send Email", "config": {"type": "send_email"}}
                    ]
                },
                {
                    "id": "daily_report",
                    "name": "Daily Report",
                    "description": "Send daily campaign performance report",
                    "steps": [
                        {"type": "trigger", "label": "On Schedule", "config": {"type": "on_schedule"}},
                        {"type": "action", "label": "Make HTTP Request", "config": {"type": "http_request"}}
                    ]
                },
                {
                    "id": "tag_leads",
                    "name": "Tag High-Value Leads",
                    "description": "Automatically tag leads based on attributes",
                    "steps": [
                        {"type": "trigger", "label": "New Lead Created", "config": {"type": "new_lead"}},
                        {"type": "condition", "label": "If Field Equals", "config": {"type": "if_field_equals"}},
                        {"type": "action", "label": "Add Tag", "config": {"type": "add_tag"}}
                    ]
                },
                {
                    "id": "auto_campaign",
                    "name": "Auto Campaign",
                    "description": "Automatically create and send campaigns",
                    "steps": [
                        {"type": "trigger", "label": "On Schedule", "config": {"type": "on_schedule"}},
                        {"type": "action", "label": "Create Campaign", "config": {"type": "create_campaign"}}
                    ]
                }
            ]
        }
    
    # ========================================================================
    # Frontend Dashboard (React App)
    # ========================================================================
    
    # Check if frontend build directory exists
    frontend_dist_path = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist_path.exists() and (frontend_dist_path / "index.html").exists():
        # Mount static files (CSS, JS, images)
        app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="static")
        
        # Serve index.html for root and all non-API routes (SPA routing)
        @app.get("/", tags=["Dashboard"])
        @app.get("/{full_path:path}", tags=["Dashboard"])
        async def serve_frontend(full_path: str = ""):
            """Serve React frontend for dashboard"""
            # Don't intercept API/health/metrics routes
            if full_path.startswith(("api", "health", "metrics", "docs", "redoc", "openapi.json")):
                raise HTTPException(status_code=404, detail="Not found")
            
            # Serve index.html for all other routes (React Router handles internal routing)
            index_path = frontend_dist_path / "index.html"
            return FileResponse(index_path)
    else:
        # Fallback: Serve old dashboard.html if frontend not built
        @app.get("/", tags=["Dashboard"])
        async def serve_legacy_dashboard():
            """Serve legacy HTML dashboard (requires frontend build for full dashboard)"""
            dashboard_path = Path(__file__).parent / "dashboard.html"
            if dashboard_path.exists():
                return FileResponse(dashboard_path)
            return {"message": "Build frontend to access dashboard", "instructions": "cd frontend && npm install && npm run build"}
    
    # ========================================================================
    # Error Handlers
    # ========================================================================
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": datetime.now().isoformat()
            }
        )

    # ========================================================================
    # Lifecycle Hooks
    # ========================================================================

    @app.on_event("startup")
    async def startup_checks():
        """Run startup checks for production readiness."""
        if config.get("redis", {}).get("required", False):
            if not app.state.redis_queue or not app.state.redis_queue.ping():
                raise RuntimeError("Redis is required but not available")

    @app.on_event("shutdown")
    async def shutdown_cleanup():
        """Release resources on shutdown."""
        if app.state.redis_queue and app.state.redis_queue.client:
            try:
                app.state.redis_queue.client.close()
            except Exception:
                pass
    
    return app
