# Database Models & Setup Guide

This guide covers setting up a persistent database for Automation Orchestrator instead of using the in-memory store.

## Current Architecture

**In-Memory Store (Default - Development)**
```python
# Currently using in-memory user store for demo
global_user_store = UserStore()
```

**Limitations:**
- Data lost on server restart
- Not suitable for production
- Single-server only
- No data persistence

## Recommended Database Solutions

### Option 1: SQLite (Recommended for Small/Medium Deployments)

**Setup:**

```bash
pip install sqlalchemy alembic
```

**User model:**
```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # Use PasswordHasher
    role = Column(String, default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class APIKeyModel(Base):
    __tablename__ = "api_keys"
    
    key_id = Column(String, primary_key=True)
    user_id = Column(String, index=True)  # Foreign key to UserModel
    key_hash = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
```

**Initialize database:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./automation_orchestrator.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
```

### Option 2: PostgreSQL (Recommended for Large/Enterprise Deployments)

**Setup:**

```bash
pip install psycopg2-binary sqlalchemy
```

**Connection string:**
```python
DATABASE_URL = "postgresql://user:password@localhost/automation_orchestrator"
```

**Initialize:**
```python
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
```

### Option 3: MongoDB (For Document-Oriented Storage)

**Setup:**

```bash
pip install motor pymongo
```

**User document:**
```python
from motor.motor_asyncio import AsyncIOMotorClient

class UserStore:
    def __init__(self, mongodb_url):
        self.client = AsyncIOMotorClient(mongodb_url)
        self.db = self.client.automation_orchestrator
        self.users = self.db.users
        self.api_keys = self.db.api_keys
    
    async def get_user_by_username(self, username: str):
        return await self.users.find_one({"username": username})
```

## Migration from In-Memory to SQLAlchemy

**Step 1: Update auth.py**

```python
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

class SQLAlchemyUserStore(UserStore):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_user_by_username(self, username: str):
        return self.db.query(UserModel).filter(
            UserModel.username == username
        ).first()
    
    def create_user(self, username: str, email: str, role: str = "viewer"):
        user = UserModel(
            user_id=f"user-{secrets.token_hex(8)}",
            username=username,
            email=email,
            role=role
        )
        self.db.add(user)
        self.db.commit()
        return user
    
    def create_api_key(self, user_id: str, name: str, expires_in_days=None):
        api_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(api_key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        key_obj = APIKeyModel(
            key_id=f"key-{secrets.token_hex(8)}",
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            expires_at=expires_at
        )
        self.db.add(key_obj)
        self.db.commit()
        return api_key, key_obj.key_id
```

**Step 2: Update API to inject database session**

```python
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user_store = SQLAlchemyUserStore(db)
    user = user_store.get_user_by_username(request.username)
    # ... rest of implementation
```

**Step 3: Initialize database on app startup**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    init_default_users(SessionLocal())
    yield
    # Shutdown (cleanup)

app = FastAPI(lifespan=lifespan)
```

## Environment Configuration

Update `.env`:

```env
# Database
DATABASE_URL=sqlite:///./automation_orchestrator.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/automation_orchestrator

# JWT
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

Update `sample_config.json`:

```json
{
  "database": {
    "type": "sqlite",
    "url": "sqlite:///./automation_orchestrator.db",
    "pool_size": 10,
    "echo": false
  }
}
```

## Database Migrations (Using Alembic)

**Initialize Alembic:**

```bash
alembic init migrations
```

**Create migration:**

```bash
alembic revision --autogenerate -m "Add users and api_keys tables"
```

**Apply migrations:**

```bash
alembic upgrade head
```

**Migration example** (`migrations/versions/001_initial.py`):

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )

def downgrade():
    op.drop_table('users')
```

## Connection Pooling & Performance

**SQLite configuration:**
```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
```

**PostgreSQL connection pooling:**
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_recycle=3600
)
```

## Data Backup & Recovery

**SQLite backup:**
```bash
cp automation_orchestrator.db automation_orchestrator.db.backup
```

**PostgreSQL backup:**
```bash
pg_dump automation_orchestrator > backup.sql
```

**PostgreSQL restore:**
```bash
psql automation_orchestrator < backup.sql
```

## Testing Database Setup

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

def test_user_creation(test_db):
    user_store = SQLAlchemyUserStore(test_db)
    user = user_store.create_user("testuser", "test@example.com")
    assert user.username == "testuser"
```

## Migration Path

**Phase 1: Current (Development)**
- In-memory UserStore
- Demo data only
- Good for prototyping

**Phase 2: SQLite (Staging)**
- SQLAlchemy backend
- Persistent storage
- Single-server deployment

**Phase 3: PostgreSQL (Production)**
- Scalable database
- Connection pooling
- Multi-server support
- Advanced monitoring

## Next Steps

1. Choose your database backend (SQLite for dev, PostgreSQL for prod)
2. Update `auth.py` with SQLAlchemyUserStore
3. Update `api.py` to inject database session
4. Create Alembic migrations
5. Test backup/recovery procedures
6. Deploy with new database configuration
