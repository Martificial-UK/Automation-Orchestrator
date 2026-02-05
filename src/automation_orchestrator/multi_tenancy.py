"""
Multi-Tenancy Foundation
Provides tenant isolation and multi-tenant support
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import uuid4
import hashlib

logger = logging.getLogger(__name__)


class Tenant:
    """Represents a customer/organization (tenant)"""
    
    def __init__(self, tenant_id: str, name: str, owner_id: str,
                 plan: str = "starter", max_leads: int = 10000):
        self.tenant_id = tenant_id
        self.name = name
        self.owner_id = owner_id
        self.plan = plan  # starter, pro, enterprise
        self.max_leads = max_leads
        self.max_users = self._get_max_users_for_plan(plan)
        
        self.active = True
        self.created_at = None
        self.updated_at = None
        
        # Tenant settings
        self.settings = {
            "crm_type": None,
            "crm_config": {},
            "features": self._get_features_for_plan(plan),
            "branding": {"logo_url": None, "primary_color": "#007bff"}
        }
        
        # Rate limiting
        self.rate_limit = self._get_rate_limit_for_plan(plan)
    
    @staticmethod
    def _get_max_users_for_plan(plan: str) -> int:
        """Get max users for plan"""
        plans = {
            "free": 1,
            "starter": 3,
            "pro": 10,
            "enterprise": 999
        }
        return plans.get(plan, 3)
    
    @staticmethod
    def _get_rate_limit_for_plan(plan: str) -> Dict[str, int]:
        """Get rate limits for plan"""
        plans = {
            "free": {"requests_per_second": 10, "leads_per_month": 100},
            "starter": {"requests_per_second": 50, "leads_per_month": 10000},
            "pro": {"requests_per_second": 200, "leads_per_month": 100000},
            "enterprise": {"requests_per_second": 1000, "leads_per_month": 999999}
        }
        return plans.get(plan, plans["starter"])
    
    @staticmethod
    def _get_features_for_plan(plan: str) -> Dict[str, bool]:
        """Get enabled features for plan"""
        features = {
            "free": {
                "api_access": True,
                "salesforce_sync": False,
                "hubspot_sync": False,
                "analytics": False,
                "rbac": False,
                "custom_branding": False
            },
            "starter": {
                "api_access": True,
                "salesforce_sync": True,
                "hubspot_sync": False,
                "analytics": True,
                "rbac": True,
                "custom_branding": False
            },
            "pro": {
                "api_access": True,
                "salesforce_sync": True,
                "hubspot_sync": True,
                "analytics": True,
                "rbac": True,
                "custom_branding": True
            },
            "enterprise": {
                "api_access": True,
                "salesforce_sync": True,
                "hubspot_sync": True,
                "analytics": True,
                "rbac": True,
                "custom_branding": True,
                "sso": True,
                "dedicated_support": True
            }
        }
        return features.get(plan, features["starter"])
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has feature enabled"""
        return self.settings.get("features", {}).get(feature, False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "plan": self.plan,
            "active": self.active,
            "max_leads": self.max_leads,
            "max_users": self.max_users,
            "rate_limit": self.rate_limit,
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class TenantManager:
    """Manage multi-tenant operations"""
    
    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.tenant_users: Dict[str, List[str]] = {}  # tenant_id -> [user_ids]
        self.logger = logging.getLogger(__name__)
    
    def create_tenant(self, name: str, owner_id: str, plan: str = "starter") -> Tenant:
        """Create a new tenant"""
        tenant_id = str(uuid4())
        
        tenant = Tenant(tenant_id, name, owner_id, plan)
        self.tenants[tenant_id] = tenant
        self.tenant_users[tenant_id] = [owner_id]
        
        self.logger.info(f"Created tenant {name} ({tenant_id}) with plan {plan}")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def update_tenant_plan(self, tenant_id: str, new_plan: str) -> bool:
        """Update tenant plan"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.plan = new_plan
        tenant.max_leads = self._get_max_leads_for_plan(new_plan)
        tenant.settings["features"] = Tenant._get_features_for_plan(new_plan)
        tenant.rate_limit = Tenant._get_rate_limit_for_plan(new_plan)
        
        self.logger.info(f"Updated tenant {tenant_id} to plan {new_plan}")
        return True
    
    @staticmethod
    def _get_max_leads_for_plan(plan: str) -> int:
        """Get max leads for plan"""
        plans = {
            "free": 100,
            "starter": 10000,
            "pro": 100000,
            "enterprise": 999999
        }
        return plans.get(plan, 10000)
    
    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.active = False
        self.logger.warning(f"Deactivated tenant {tenant_id}")
        return True
    
    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.active = True
        self.logger.info(f"Activated tenant {tenant_id}")
        return True
    
    def add_user_to_tenant(self, tenant_id: str, user_id: str) -> bool:
        """Add user to tenant"""
        if tenant_id not in self.tenant_users:
            return False
        
        if user_id not in self.tenant_users[tenant_id]:
            self.tenant_users[tenant_id].append(user_id)
            self.logger.info(f"Added user {user_id} to tenant {tenant_id}")
        
        return True
    
    def remove_user_from_tenant(self, tenant_id: str, user_id: str) -> bool:
        """Remove user from tenant"""
        if tenant_id not in self.tenant_users:
            return False
        
        if user_id in self.tenant_users[tenant_id]:
            self.tenant_users[tenant_id].remove(user_id)
            self.logger.info(f"Removed user {user_id} from tenant {tenant_id}")
        
        return True
    
    def get_tenant_users(self, tenant_id: str) -> List[str]:
        """Get all users in tenant"""
        return self.tenant_users.get(tenant_id, [])
    
    def get_user_tenants(self, user_id: str) -> List[str]:
        """Get all tenants for a user"""
        return [tid for tid, users in self.tenant_users.items() if user_id in users]
    
    def list_tenants(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all tenants"""
        tenants = self.tenants.values()
        
        if active_only:
            tenants = [t for t in tenants if t.active]
        
        return [t.to_dict() for t in tenants]


class TenantContext:
    """Request context for current tenant"""
    
    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.request_id = str(uuid4())
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id
        }


class TenantAwareQuery:
    """Base class for tenant-aware queries"""
    
    @staticmethod
    def add_tenant_filter(query: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Add tenant filter to query"""
        query["tenant_id"] = tenant_id
        return query
    
    @staticmethod
    def filter_results(results: List[Dict[str, Any]], tenant_id: str) -> List[Dict[str, Any]]:
        """Filter results to only include tenant's data"""
        return [r for r in results if r.get("tenant_id") == tenant_id]


class TenantDataIsolation:
    """Enforce tenant data isolation"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.logger = logging.getLogger(__name__)
    
    def validate_tenant_access(self, tenant_id: str, user_id: str) -> bool:
        """Validate that user has access to tenant"""
        users = self.tenant_manager.get_tenant_users(tenant_id)
        return user_id in users
    
    def enforce_isolation(self, records: List[Dict[str, Any]], 
                         tenant_id: str) -> List[Dict[str, Any]]:
        """Enforce tenant isolation on data"""
        # Only return records belonging to this tenant
        return [r for r in records if r.get("tenant_id") == tenant_id]
    
    def add_tenant_identifier(self, record: Dict[str, Any], 
                             tenant_id: str) -> Dict[str, Any]:
        """Add tenant identifier to record"""
        record["tenant_id"] = tenant_id
        record["_hash"] = self._compute_hash(tenant_id, record.get("id"))
        return record
    
    @staticmethod
    def _compute_hash(tenant_id: str, record_id: str) -> str:
        """Compute hash for data integrity verification"""
        content = f"{tenant_id}:{record_id}".encode()
        return hashlib.sha256(content).hexdigest()[:16]
    
    def validate_record_ownership(self, record: Dict[str, Any], 
                                 tenant_id: str) -> bool:
        """Validate that record belongs to tenant"""
        if record.get("tenant_id") != tenant_id:
            self.logger.warning(
                f"Unauthorized access attempt: tenant {tenant_id} "
                f"accessing record of tenant {record.get('tenant_id')}"
            )
            return False
        
        return True
