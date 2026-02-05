"""
REST API for Automation Orchestrator
Provides endpoints for workflow control, lead management, and CRM integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import uuid
from pathlib import Path
from automation_orchestrator.audit import get_audit_logger
from automation_orchestrator.deduplication import DeduplicationEngine
from automation_orchestrator.rbac import RBACManager, Role, Permission, User
from automation_orchestrator.analytics import Analytics
from automation_orchestrator.multi_tenancy import TenantManager, TenantContext
from automation_orchestrator.auth import (
    JWTHandler, PasswordHasher, APIKeyManager, UserStore,
    global_user_store, LoginRequest, LoginResponse, APIKeyCreateRequest,
    APIKeyResponse
)

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
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(),
            components={
                "api": "running",
                "audit": "running",
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
            app.state._health_cache = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "api": "running",
                    "cache": "active",
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
        """Get system metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "requests_total": "N/A",
                "requests_failed": "N/A",
                "leads_processed": "N/A",
                "workflows_executed": "N/A",
                "uptime_seconds": "N/A"
            }
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
                status="created",
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
            if not app.state.workflow_runner:
                raise HTTPException(status_code=500, detail="Workflow runner not configured")
            
            execution_id = str(uuid.uuid4())
            
            audit.log_event(
                event_type="workflow_started",
                details={
                    "execution_id": execution_id,
                    "workflow_id": trigger.workflow_id
                }
            )
            
            # Execute workflow in background
            background_tasks.add_task(
                app.state.workflow_runner.execute_workflow,
                workflow_id=trigger.workflow_id,
                execution_id=execution_id,
                lead_data=trigger.lead_data,
                context=trigger.custom_context
            )
            
            return WorkflowResponse(
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
            if not app.state.workflow_runner:
                raise HTTPException(status_code=500, detail="Workflow runner not configured")
            
            status = app.state.workflow_runner.get_status(workflow_id)
            return {"workflow_id": workflow_id, "status": status}
        
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
    
    # ========================================================================
    # Campaign Endpoints (Continued)
    # ========================================================================
    
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
    async def send_email(
        lead_id: str,
        template_id: str,
        custom_subject: Optional[str] = None,
        background_tasks: BackgroundTasks = None
    ):
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
            
            background_tasks.add_task(
                app.state.email_followup.send_email,
                lead_id=lead_id,
                template_id=template_id,
                subject=custom_subject,
                execution_id=execution_id
            )
            
            audit.log_event(
                event_type="email_sent",
                lead_id=lead_id,
                details={"template_id": template_id}
            )
            
            return {
                "status": "sent",
                "execution_id": execution_id,
                "lead_id": lead_id,
                "timestamp": datetime.now().isoformat()
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
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
        return app.state.analytics.get_dashboard_summary(days)
    
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
    # RBAC Endpoints
    # ========================================================================
    
    @app.post("/api/users", tags=["RBAC"])
    async def create_user(username: str, role: str, email: str = ""):
        """Create a new user"""
        try:
            user = app.state.rbac.create_user(
                str(uuid.uuid4()),
                username,
                Role[role.upper()],
                email
            )
            return user.to_dict()
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
    async def update_user_role(user_id: str, role: str):
        """Update user role"""
        try:
            success = app.state.rbac.update_user_role(user_id, Role[role.upper()])
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            return {"status": "updated", "role": role}
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
    async def create_tenant(name: str, owner_id: str, plan: str = "starter"):
        """Create a new tenant"""
        try:
            tenant = app.state.tenants.create_tenant(name, owner_id, plan)
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
    # Dashboard
    # ========================================================================
    
    @app.get("/", tags=["Dashboard"])
    async def serve_dashboard():
        """Serve the web dashboard"""
        dashboard_path = Path(__file__).parent / "dashboard.html"
        if dashboard_path.exists():
            return FileResponse(dashboard_path)
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
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
    
    return app
