"""
RBAC (Role-Based Access Control) System
Manages user roles, permissions, and access control
"""

import logging
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime, timezone
import hashlib

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"              # Full access
    MANAGER = "manager"          # Team management + lead access
    SALESPERSON = "salesperson"  # Lead access only
    ANALYST = "analyst"          # Read-only analytics
    GUEST = "guest"              # Limited read-only


class Permission(str, Enum):
    """System permissions"""
    # Lead permissions
    LEAD_CREATE = "lead:create"
    LEAD_READ = "lead:read"
    LEAD_UPDATE = "lead:update"
    LEAD_DELETE = "lead:delete"
    LEAD_EXPORT = "lead:export"
    
    # Workflow permissions
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_EXECUTE = "workflow:execute"
    
    # CRM permissions
    CRM_CONFIG = "crm:config"
    CRM_SYNC = "crm:sync"
    
    # User management
    USER_MANAGE = "user:manage"
    USER_READ = "user:read"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    
    # System
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"


# Role -> Permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.MANAGER: {
        Permission.LEAD_CREATE, Permission.LEAD_READ, Permission.LEAD_UPDATE,
        Permission.LEAD_EXPORT, Permission.WORKFLOW_READ, Permission.WORKFLOW_EXECUTE,
        Permission.ANALYTICS_READ, Permission.USER_READ, Permission.CRM_SYNC
    },
    Role.SALESPERSON: {
        Permission.LEAD_CREATE, Permission.LEAD_READ, Permission.LEAD_UPDATE,
        Permission.LEAD_EXPORT, Permission.WORKFLOW_READ
    },
    Role.ANALYST: {
        Permission.LEAD_READ, Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT
    },
    Role.GUEST: {
        Permission.LEAD_READ, Permission.ANALYTICS_READ
    }
}


class User:
    """User with role and permissions"""
    
    def __init__(self, user_id: str, username: str, role: Role, 
                 email: str = "", active: bool = True):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.email = email
        self.active = active
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_login = None
        self.custom_permissions: Set[Permission] = set()
    
    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for user"""
        base_permissions = ROLE_PERMISSIONS.get(self.role, set()).copy()
        return base_permissions | self.custom_permissions
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        if not self.active:
            return False
        
        if self.role == Role.ADMIN:
            return True
        
        return permission in self.get_permissions()
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the permissions"""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all permissions"""
        return all(self.has_permission(p) for p in permissions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "email": self.email,
            "active": self.active,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "permissions": [p.value for p in self.get_permissions()]
        }


class RBACManager:
    """Manage users, roles, and permissions"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_user(self, user_id: str, username: str, role: Role, 
                   email: str = "") -> User:
        """Create a new user"""
        if user_id in self.users:
            raise ValueError(f"User {user_id} already exists")
        
        user = User(user_id, username, role, email)
        self.users[user_id] = user
        
        self.logger.info(f"Created user {username} with role {role.value}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def update_user_role(self, user_id: str, role: Role) -> bool:
        """Update user role"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.role = role
        self.logger.info(f"Updated user {user_id} role to {role.value}")
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.active = False
        self.logger.warning(f"Deactivated user {user_id}")
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.active = True
        self.logger.info(f"Activated user {user_id}")
        return True
    
    def grant_custom_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant additional permission to user"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.custom_permissions.add(permission)
        self.logger.info(f"Granted {permission.value} to {user_id}")
        return True
    
    def revoke_custom_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke permission from user"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.custom_permissions.discard(permission)
        self.logger.info(f"Revoked {permission.value} from {user_id}")
        return True
    
    def list_users(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all users"""
        users = self.users.values()
        
        if active_only:
            users = [u for u in users if u.active]
        
        return [u.to_dict() for u in users]
    
    def get_users_with_permission(self, permission: Permission) -> List[User]:
        """Get all users with specific permission"""
        return [u for u in self.users.values() if u.has_permission(permission)]
    
    def get_users_with_role(self, role: Role) -> List[User]:
        """Get all users with specific role"""
        return [u for u in self.users.values() if u.role == role]


class AccessControl:
    """Access control middleware for API"""
    
    def __init__(self, rbac_manager: RBACManager):
        self.rbac = rbac_manager
        self.logger = logging.getLogger(__name__)
    
    def require_role(self, required_role: Role):
        """Decorator to require specific role"""
        def decorator(func):
            def wrapper(*args, current_user: Optional[User] = None, **kwargs):
                if not current_user:
                    raise PermissionError("User not authenticated")
                
                # Admin bypasses role checks
                if current_user.role == Role.ADMIN:
                    return func(*args, current_user=current_user, **kwargs)
                
                if current_user.role != required_role:
                    self.logger.warning(
                        f"Access denied: {current_user.username} "
                        f"needs {required_role.value}"
                    )
                    raise PermissionError(f"Requires {required_role.value} role")
                
                return func(*args, current_user=current_user, **kwargs)
            return wrapper
        return decorator
    
    def require_permission(self, required_permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            def wrapper(*args, current_user: Optional[User] = None, **kwargs):
                if not current_user:
                    raise PermissionError("User not authenticated")
                
                if not current_user.has_permission(required_permission):
                    self.logger.warning(
                        f"Access denied: {current_user.username} "
                        f"lacks {required_permission.value}"
                    )
                    raise PermissionError(
                        f"Requires {required_permission.value} permission"
                    )
                
                return func(*args, current_user=current_user, **kwargs)
            return wrapper
        return decorator
    
    def require_any_permission(self, permissions: List[Permission]):
        """Decorator to require any of the permissions"""
        def decorator(func):
            def wrapper(*args, current_user: Optional[User] = None, **kwargs):
                if not current_user:
                    raise PermissionError("User not authenticated")
                
                if not current_user.has_any_permission(permissions):
                    perms = [p.value for p in permissions]
                    self.logger.warning(
                        f"Access denied: {current_user.username} "
                        f"lacks any of {perms}"
                    )
                    raise PermissionError(f"Requires one of: {perms}")
                
                return func(*args, current_user=current_user, **kwargs)
            return wrapper
        return decorator
