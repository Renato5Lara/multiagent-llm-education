# DB-002: Sync SQLAlchemy Session in Async FastAPI Application

**Severity**: HIGH  
**Component**: Database session infrastructure  
**Files**: `backend/app/db/session.py`, `backend/app/api/deps.py`  
**Status**: REPORTED (requires systematic migration to asyncpg)

---

## Root Cause

FastAPI is an async ASGI server. All request handlers run on an async event loop. However, the database session is synchronous:

```python
# app/db/session.py (line 31)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# app/api/deps.py (lines 20-25)
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Every `db.query()`, `db.commit()`, `db.flush()` call **blocks the event loop thread** for the duration of the database I/O.

## Impact

- Every API request blocks the event loop for ALL database queries
- Under load (10+ concurrent requests), the event loop thread saturates
- Pool size `5` → `max_overflow 10` → max 15 connections. 16th request blocks
- SSE streaming endpoints (e.g., `/api/students/tutor/stream`) share the same blocked loop
- Typical dashboard request: 3 sync queries = 3 event loop blocks
- No cooperative multitasking during I/O

## Fix Required

### 1. Add async engine + session

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async_engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    pool_size=5, max_overflow=10, pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False,
)
```

### 2. Convert `get_db` to async

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### 3. Convert ALL 29 service files

Every `db.query(...)` → `await db.execute(...)`, `db.commit()` → `await db.commit()`, etc.

## Effort Estimate

- 29 service files, ~3000 lines of query code
- Requires systematic conversion: `query()` → `execute(select(...))`, scalar → `scalar()`, `.all()` → `.scalars().all()`
- High risk of regression — every query path must be verified
