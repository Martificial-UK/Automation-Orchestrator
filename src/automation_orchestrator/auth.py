"""
Authentication and Authorization Module
Handles JWT tokens, user authentication, and API key management
"""

import os
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Security constants
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-strong-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
API_KEY_PREFIX = "ao_"  # Automation Orchestrator


class User(BaseModel):
    """User model"""
    user_id: str
    username: str
    email: str
    role: str  # admin, lead_manager, viewer
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: list = Field(default_factory=list)


class APIKey(BaseModel):
    """API Key model"""
    key_id: str
    key_hash: str  # Hashed API key
    name: str
    user_id: str
    is_active: bool = True
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload"""
    user_id: str
    username: str
    role: str
    exp: datetime


class APIKeyCreateRequest(BaseModel):
    """API key creation request"""
    name: str
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (only shown on creation)"""
    key_id: str
    api_key: str  # Only shown once at creation
    name: str
    created_at: datetime


class PasswordHasher:
    """Password hashing utility"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${pwd_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = password_hash.split('$')
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return new_hash.hex() == pwd_hash
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class JWTHandler:
    """JWT token handling"""
    
    @staticmethod
    def create_token(user_id: str, username: str, role: str, hours: int = JWT_EXPIRATION_HOURS) -> str:
        """Create JWT token"""
        exp = datetime.now(timezone.utc) + timedelta(hours=hours)
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": exp,
            "iat": datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    @staticmethod
    def get_token_expiration_hours() -> int:
        """Get token expiration in hours"""
        return JWT_EXPIRATION_HOURS


class APIKeyManager:
    """API Key management"""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        random_part = secrets.token_urlsafe(32)
        return f"{API_KEY_PREFIX}{random_part}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, api_key_hash: str) -> bool:
        """Verify API key matches hash"""
        return APIKeyManager.hash_api_key(api_key) == api_key_hash


class UserStore:
    """In-memory user store (replace with database)"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self._init_default_users()
    
    def _init_default_users(self):
        """Initialize default admin user"""
        admin_user = User(
            user_id="admin-001",
            username="admin",
            email="admin@example.com",
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            permissions=["read:all", "write:all", "admin:all"]
        )
        self.users["admin"] = admin_user
        logger.info("Default admin user initialized")
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.users.get(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None
    
    def create_user(self, username: str, email: str, role: str = "viewer") -> User:
        """Create new user"""
        if username in self.users:
            raise ValueError(f"User {username} already exists")
        
        user = User(
            user_id=f"user-{secrets.token_hex(8)}",
            username=username,
            email=email,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            permissions=self._get_permissions_for_role(role)
        )
        self.users[username] = user
        logger.info(f"User created: {username} with role {role}")
        return user
    
    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update user role"""
        for user in self.users.values():
            if user.user_id == user_id:
                user.role = new_role
                user.permissions = self._get_permissions_for_role(new_role)
                logger.info(f"User {user.username} role updated to {new_role}")
                return True
        return False
    
    def update_last_login(self, user_id: str):
        """Update last login timestamp"""
        for user in self.users.values():
            if user.user_id == user_id:
                user.last_login = datetime.utcnow()
                return
    
    def create_api_key(self, user_id: str, name: str, expires_in_days: Optional[int] = None) -> tuple:
        """Create API key for user (returns api_key, key_id)"""
        api_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(api_key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        key_id = f"key-{secrets.token_hex(8)}"
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        self.api_keys[key_id] = api_key_obj
        logger.info(f"API key created for user {user_id}: {name}")
        return api_key, key_id
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key and return associated user"""
        api_key_hash = APIKeyManager.hash_api_key(api_key)
        
        for key_id, key_obj in self.api_keys.items():
            if key_obj.key_hash == api_key_hash and key_obj.is_active:
                # Check expiration
                if key_obj.expires_at and datetime.utcnow() > key_obj.expires_at:
                    logger.warning(f"API key expired: {key_id}")
                    continue
                
                # Update last used
                key_obj.last_used = datetime.utcnow()
                
                # Get associated user
                user = self.get_user_by_id(key_obj.user_id)
                return user
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            logger.info(f"API key revoked: {key_id}")
            return True
        return False
    
    def list_api_keys(self, user_id: str):
        """List API keys for user (without showing the actual key)"""
        keys = []
        for key_obj in self.api_keys.values():
            if key_obj.user_id == user_id:
                keys.append({
                    "key_id": key_obj.key_id,
                    "name": key_obj.name,
                    "is_active": key_obj.is_active,
                    "created_at": key_obj.created_at,
                    "last_used": key_obj.last_used,
                    "expires_at": key_obj.expires_at,
                    "key_preview": f"{API_KEY_PREFIX}...{key_obj.key_hash[-8:]}"
                })
        return keys
    
    @staticmethod
    def _get_permissions_for_role(role: str) -> list:
        """Get permissions for role"""
        permissions_map = {
            "admin": [
                "read:all", "write:all", "delete:all", "admin:all",
                "manage:users", "manage:api_keys", "view:audit"
            ],
            "lead_manager": [
                "read:leads", "write:leads", "read:workflows", 
                "write:workflows", "read:analytics", "write:email"
            ],
            "viewer": [
                "read:leads", "read:workflows", "read:analytics", "read:email"
            ]
        }
        return permissions_map.get(role, [])


# Global user store (replace with database in production)
global_user_store = UserStore()
