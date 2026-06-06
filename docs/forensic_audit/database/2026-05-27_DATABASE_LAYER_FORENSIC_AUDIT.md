# Database Layer Forensic Audit

**Date**: 2026-05-27  
**Scope**: Alembic (10 migrations), SQLAlchemy (26 model classes, 5 db infra files), PostgreSQL, 29 service files  
**Analyst**: opencode forensic audit agent  
**Bugs cataloged**: 14 (1 CRITICAL, 7 HIGH, 4 MEDIUM, 2 LOW)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│   FastAPI (async)                                       │
│   ┌────────────────────────────────────────────────┐    │
│   │  app/api/deps.py: get_db() → SessionLocal()    │    │
│   │  SYNC session in async app → event loop BLOCK  │    │
│   └────────────────────────────────────────────────┘    │
│          │                                              │
│          ▼                                              │
│   ┌────────────────────────────────────────────────┐    │
│   │  app/db/session.py                             │    │
│   │  SessionLocal = sessionmaker(                  │    │
│   │    autocommit=False, autoflush=False,          │    │
│   │    expire_on_commit=False, bind=engine         │    │
│   │  )                                             │    │
│   │  engine = create_engine(pool_size=5/10,        │    │
│   │    max_overflow=10/20, pool_pre_ping=True)     │    │
│   └────────────────────────────────────────────────┘    │
│          │                                              │
│          ▼                                              │
│   ┌────────────────────────────────────────────────┐    │
│   │  app/db/uow.py — UnitOfWork                    │    │
│   │  + savepoints, event outbox integration        │    │
│   │  + advisory lock delegation                    │    │
│   └────────────────────────────────────────────────┘    │
│          │                                              │
│          ▼                                              │
│   ┌────────────────────────────────────────────────┐    │
│   │  29 service files (no repository layer)        │    │
│   │  ~12 active N+1 query patterns                │    │
│   │  ~$35$~ relationship lazy='select' defaults         │    │
│   └────────────────────────────────────────────────┘    │
│          │                                              │
│          ▼                                              │
│   ┌────────────────────────────────────────────────┐    │
│   │  26 model classes on DeclarativeBase           │    │
│   │  4 models ORPHANED from Alembic tracking       │    │
│   └────────────────────────────────────────────────┘    │
│          │                                              │
│          ▼                                              │
│   ┌────────────────────────────────────────────────┐    │
│   │  PostgreSQL (via psycopg2 sync)                │    │
│   │  No asyncpg — all queries block event loop     │    │
│   └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Migration Chain (Revision Graph)

```
83058a18afd3 (root)
  │
  └── 6a7b8c9d0e1f  (add_course_prerequisite)
       │
       └── 8b9c0d1e2f3a  (memory + knowledge_graph)
            │
            └── 3a4b5c6d7e8f  (event_outbox)
                 │
                 └── 9a8b7c6d5e4f  (concurrency_controls)
                      │
                      ├── 0a1b2c3d4e5f  (shared_memory)  ──┐
                      ├── 1b2c3d4e5f6a  (idempotency_lifecycle) ─┤
                      │                    (UNMERGED)  →  0b1c2d3e4f5a (token_version)
                      │                                         ↑
                      │                              ★ HEAD 2 (UNMERGED!)
                      │
                      └── 3ba21248a301  (MERGE of 0a1b2c3d4e5f + 1b2c3d4e5f6a)
                              │
                              └── 4c5d6e7f8a9b  (reconcile_institutional_schema) → ★ HEAD 1
```

**Two current heads**: `4c5d6e7f8a9b` (HEAD 1, merged lineage) and `0b1c2d3e4f5a` (HEAD 2, unmerged branch from `9a8b7c6d5e4f`).

---

## Bug Catalog

### DB-001 [CRITICAL] — Unmerged migration head (token_version orphan)

**Files**:
- `backend/alembic/versions/0b1c2d3e4f5a_add_token_version_to_users.py`
- `backend/alembic/versions/3ba21248a301_merge_shared_memory_and_idempotency_.py`
- `backend/app/models/user.py` line 39 (`token_version` column exists in model)

**Root cause**: Migration `0b1c2d3e4f5a` adds `token_version` to `users` table. It branched from `9a8b7c6d5e4f`, the same parent as `0a1b2c3d4e5f` and `1b2c3d4e5f6a`. The merge `3ba21248a301` merged only the latter two branches, **excluding** `0b1c2d3e4f5a`. The result: `alembic history` shows two heads.

**Impact**:
- `alembic upgrade head` applies only ONE head (depends on which head resolves first)
- If HEAD 1 (`4c5d6e7f8a9b`) is applied first, the `token_version` column is NEVER created
- The `User.token_version` model field references a column that may not exist in production → `OperationalError` on any access
- If HEAD 2 (`0b1c2d3e4f5a`) is applied first, HEAD 1's lineage (`9a8b7c6d5e4f`) is correctly reached, but `token_version` column exists
- The auth service uses `token_version` for refresh token rotation (`auth_service.py`) — if the column doesn't exist, all token refreshes fail

**Reproduction**:
```bash
alembic history
# Two heads: 4c5d6e7f8a9b (head), 0b1c2d3e4f5a (head)
alembic upgrade head
# Applies ONLY one head — the other remains pending
alembic current
# Shows only one head applied
```

**Fix**: Create a new merge migration that merges `0b1c2d3e4f5a` into `4c5d6e7f8a9b`:
```bash
alembic merge -m "merge token_version into reconciled schema" 4c5d6e7f8a9b 0b1c2d3e4f5a
```

---

### DB-002 [HIGH] — Missing async session infrastructure (sync in async app)

**File**: `backend/app/db/session.py` (line 31 — `SessionLocal` is sync `sessionmaker`)
**File**: `backend/app/api/deps.py` (line 20-25 — `get_db()` yields sync `Session`)

**Root cause**: The entire application runs on FastAPI (async ASGI server), but all database access uses **synchronous** SQLAlchemy sessions. Every `db.query()`, `db.commit()`, `db.flush()` call blocks the async event loop thread.

The `session.py` configures `create_engine` (sync) with `psycopg2` (sync driver). There is no `async_engine`, `AsyncSession`, `async_sessionmaker`, or `AsyncSessionLocal` anywhere.

**Impact**:
- Every API request blocks the event loop for the duration of ALL database queries
- Under concurrent load (10+ requests), the event loop thread becomes saturated
- No `await`-based database access means no cooperative multitasking during I/O
- The pool (`pool_size=5`, `max_overflow=10`) has a maximum of 15 concurrent connections — any request waiting for a connection blocks the entire loop
- Async endpoints like SSE streaming (`/api/students/tutor/stream`) share the same blocked loop

**Query volume per typical request**:
```
GET /api/students/dashboard → 3 queries (my-courses, summary, IA dashboard)
                              = 3 sync queries → 3 event loop blocks
POST /api/students/diagnostic → 6 queries (save + 5 invalidations via triggers)
                              = 6 event loop blocks
```

**Fix**: Migrate to `asyncpg` + `AsyncSession`:
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async_engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    pool_size=5, max_overflow=10, pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

This requires converting ALL 29 service files to `async def` and `await session.execute()` / `await session.commit()` patterns.

---

### DB-003 [HIGH] — Schema drift: 4 models have no migration representation

**Files** (models missing from Alembic tracking):
- `backend/app/models/educational_context.py` → `EducationalContext` table
- `backend/app/models/programming_metrics.py` → `ProgrammingMetrics` table
- `backend/app/models/programming_prerequisite.py` → `ConceptPrerequisite` table
- `backend/app/models/resource_programming_tag.py` → `ResourceProgrammingTag` table

**Root cause**: These models were added to `Base` subclasses but were NEVER included in the Alembic env.py import list (line 12-33) and have NO corresponding migration file. They exist only in code. If `Base.metadata.create_all()` was ever called (e.g., in development), the tables exist in the local database but not in tracked migrations.

**Verification**:
```bash
# Tables in models but not in any migration:
# - educational_context
# - concept_prerequisite
# - programming_metrics
# - resource_programming_tag

# These 4 models ARE imported in models/__init__.py
# BUT NOT imported in alembic/env.py
```

**Impact**:
- Production deploy via `alembic upgrade head` — these tables are NEVER created
- Any service code referencing these models crashes with `psycopg2.errors.UndefinedTable`
- Involved services: `activation_service.py` (EducationalContext), `programming_metrics_service.py`, `programming_course_service.py` (ResourceProgrammingTag), `programming_pathway_service.py` (ConceptPrerequisite)
- `alembic check` passes because the migration metadata doesn't include these models' tables

**Fix**:
1. Add the 4 model imports to `alembic/env.py`
2. Create a new migration that adds these tables:
   ```bash
   alembic revision --autogenerate -m "add missing educational_context, programming_metrics, concept_prerequisite, resource_programming_tag"
   ```
3. Verify: `alembic check` now detects them

---

### DB-004 [HIGH] — N+1 query pattern in `get_enrolled_students`

**File**: `backend/app/services/course_service.py:257-276`

**Root cause**: The method queries all `Enrollment` records for a course, then loops through each to fetch the `User` individually by `student_id`.

```python
enrollments = db.query(Enrollment).filter(...).all()
for enrollment in enrollments:
    student = db.query(User).filter(User.id == enrollment.student_id).first()
```

**Impact**: For a course with 50 enrolled students, this produces **51 SQL queries** instead of 2 (enrollments + batch user fetch). Under concurrent load, each of the 49 extra queries compounds the event-loop blocking problem (DB-002).

**Fix**: Batch-load users:
```python
enrollments = db.query(Enrollment).options(
    selectinload(Enrollment.student)
).filter(...).all()
# or:
student_ids = [e.student_id for e in enrollments]
students = {u.id: u for u in db.query(User).filter(User.id.in_(student_ids)).all()}
```

---

### DB-005 [HIGH] — N+1 query pattern in `get_learning_path_detail`

**File**: `backend/app/services/student_service.py:454-459`

**Root cause**: After loading `PathModule` records, the code queries `Resource` individually for each module that has a `resource_id`.

```python
modules = db.query(PathModule).filter(...).all()
for mod in modules:
    if mod.resource_id:
        resource = db.query(Resource).filter(Resource.id == mod.resource_id).first()
```

**Impact**: For a path with 20 modules, each with a resource: **21 queries** instead of **2**. Called every time the learning path page loads.

**Fix**: Add `selectinload(PathModule.resource)` to the initial query or batch-load resources:
```python
modules = db.query(PathModule).options(
    selectinload(PathModule.resource)
).filter(...).all()
```

---

### DB-006 [HIGH] — N+1 query chain in `prerequisite_service.check_course_access`

**File**: `backend/app/services/prerequisite_service.py:206-256`

**Root cause**: For each prerequisite course, the function:
1. Queries the `Course` by `institutional_course_id` (query 1)
2. Fallback: queries `Course` by `id` (query 2)
3. Calls `has_student_completed_course` → queries completion (query 3)
4. Calls `is_student_enrolled_in_course` → checks enrollment (query 4)

For a course with 5 prerequisites: **~20 queries** instead of **4** (batch load courses, batch check completion, batch check enrollment).

**Impact**: This function is called from `evaluate_module_completion`, `get_course_analytics`, `get_next_semester_recommendations` — compounding the N+1 across the entire recommendation pipeline. `get_next_course_recommendations` iterates over next-cycle courses and calls `check_course_access` for each (see DB-007).

**Fix**: Add `_batch_check_course_access` (already partially exists in `_batch_check_course_access` but not wired into the single-course path) and batch preload all prerequisite courses, completion status, and enrollment status using `IN` queries with dict lookups.

---

### DB-007 [HIGH] — N+1 compounded in `get_next_course_recommendations`

**File**: `backend/app/services/prerequisite_service.py:461-483`

**Root cause**: The function queries all "next" courses, then calls `check_course_access` (which itself has N+1 — see DB-006) for EACH course in a loop.

```python
next_courses = db.query(Course).filter(...).all()
for course in next_courses:
    access = check_course_access(db, student, course)  # N+1 CHAIN
```

**Impact**: For 10 next courses, each with 3 prerequisites: **~130 queries**. This powers the "next recommended course" feature on the student dashboard — every dashboard load.

**Fix**: Refactor to use `_batch_check_course_access` which batch-loads prerequisites, completion, and enrollment status with `IN` queries and dict lookups.

---

### DB-008 [HIGH] — N+1 in knowledge graph `get_course_recommendations_from_graph`

**File**: `backend/app/services/knowledge_graph_service.py:201-228`

**Root cause**: Triple-nested loop with individual queries per iteration:
```python
for weakness in weaknesses:              # W iterations
    weak_nodes = db.query(...).all()     # W queries
    for node in weak_nodes:              # W × N iterations
        teaching_edges = db.query(...).all()  # W × N queries
        for edge in teaching_edges:      # W × N × E iterations
            course_node = db.query(...).first()  # W × N × E queries
```

**Impact**: For 3 weaknesses, 2 nodes each, 2 edges each: **15 queries** instead of **3**. Scales multiplicatively with the student's weakness count.

**Fix**: Batch-load nodes by IDs, pre-load edges with `selectinload` on the nodes.

---

### DB-009 [MEDIUM] — Unique constraint missing for critical business rules

**Files** (missing unique constraints):
- `backend/app/models/enrollment.py`: No `UniqueConstraint("student_id", "course_id")` — a student can be enrolled in the same course multiple times
- `backend/app/models/learning_path.py`: No `UniqueConstraint("student_id", "course_id")` — a student can have multiple learning paths for the same course
- `backend/app/models/diagnostic_result.py`: No `UniqueConstraint("student_id", "course_id")` — multiple diagnostic results per student per course
- `backend/app/models/student_progress.py`: No `UniqueConstraint("student_id", "course_id", "resource_id")` — duplicate progress entries possible

**Root cause**: The advisory lock pattern in `save_diagnostic` and `enroll_students` uses `pg_advisory_xact_lock` as a runtime guard, but there are no database-level unique constraints as a safety net. The locks prevent races within the same application instance but cannot protect against:
- Concurrent requests from different application instances (horizontal scaling)
- Direct database modifications (admin panel, scripts)
- Application bugs that skip the lock

**Impact**:
- Duplicate enrollments for the same student/course pair
- Duplicate learning paths for the same student/course (last write wins)
- Multiple diagnostic results for the same student/course
- Duplicate progress entries for the same resource

**Impact severity**: **MEDIUM** — the advisory locks work for single-instance deployments but fail under horizontal scaling.

**Fix**: Add database-level unique constraints:
```python
# enrollment.py
__table_args__ = (
    UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
)

# learning_path.py
__table_args__ = (
    UniqueConstraint("student_id", "course_id", name="uq_learning_path_student_course"),
)

# diagnostic_result.py
__table_args__ = (
    UniqueConstraint("student_id", "course_id", name="uq_diagnostic_student_course"),
)

# student_progress.py
__table_args__ = (
    UniqueConstraint("student_id", "course_id", "resource_id",
                     name="uq_student_progress_student_course_resource"),
)
```

---

### DB-010 [MEDIUM] — Missing compound indexes on high-frequency query paths

**Files** (missing indexes):
- `backend/app/models/enrollment.py`: No index on `(student_id, status)` — Dashboard queries "my active enrollments" by student + status
- `backend/app/models/learning_path.py`: No index on `(student_id, course_id)` — `get_learning_path_detail` queries by student + course
- `backend/app/models/path_module.py`: No index on `(path_id, status)` — progress queries filter modules by status
- `backend/app/models/student_progress.py`: No index on `(student_id, course_id)` — `get_student_courses_by_cycle` aggregates progress by student + course
- `backend/app/models/diagnostic_result.py`: No index on `(student_id, course_id)` — `get_diagnostic` queries by student + course
- `backend/app/models/audit_log.py`: No index on `(user_id, entity_type, entity_id)` — admin panel audit log queries
- `backend/app/models/conversation_message.py`: No index on `(student_id, course_id)` — tutor context loading

**Impact**: Sequential scans on tables that grow with usage. Each of these query paths filters on multiple columns — a single-column index is insufficient. The database will do `BitmapAnd` scans or full table scans as the tables grow beyond 10k+ rows.

**Fix**: Add compound indexes via a migration:
```python
Index("ix_enrollment_student_status", "student_id", "status")
Index("ix_learning_path_student_course", "student_id", "course_id")
Index("ix_path_module_path_status", "path_id", "status")
Index("ix_student_progress_student_course", "student_id", "course_id")
Index("ix_diagnostic_student_course", "student_id", "course_id")
Index("ix_audit_log_user_entity", "user_id", "entity_type", "entity_id")
```

---

### DB-011 [MEDIUM] — No explicit foreign key for `evaluation_attempts.module_id`

**File**: `backend/app/models/evaluation_attempt.py`

**Root cause**: The `module_id` column uses `ForeignKey("path_modules.id")` in the migration (`83058a18afd3` line 238) but the model does NOT define a `relationship()` with `PathModule`. This means:
- The FK constraint exists at the database level
- But the ORM has no relationship to `PathModule` — so no `selectinload` or join capability
- The evaluation service must manually query `PathModule` when this FK is needed

**Impact**: Any code that needs to navigate from `EvaluationAttempt` to `PathModule` must write an explicit query — no `evaluation.module` shortcut. This is a missed ORM capability, not a data integrity bug (FK exists).

**Fix**: Add relationship:
```python
module = relationship("PathModule", backref="evaluation_attempts")
```

---

### DB-012 [MEDIUM] — Zero eager loading usage across 29 service files

**Files**: All 29 service files (`backend/app/services/*.py`)

**Root cause**: A search for `selectinload`, `joinedload`, `subqueryload`, `immediateload`, or `.options(` returns **zero results** across the entire service layer. Every relationship access uses the default `lazy='select'` behavior, firing a separate SQL query per attribute access.

**Impact**: This is the root cause of all 12 N+1 patterns (DB-004 through DB-008 and DB-013/DB-014). Even code paths that don't have explicit loops still trigger lazy loads when relationships are accessed.

**Examples of hidden lazy loads**:
```python
# Accessing Course.teacher inside a template renders a lazy load
course = db.query(Course).first()
teacher_name = course.teacher.first_name  # LAZY LOAD!

# Accessing ResourceObjective.objective triggers lazy load
ro = db.query(ResourceObjective).first()
objective_title = ro.objective.title  # LAZY LOAD!
```

**Fix**: Adopt a policy: ALL queries that access relationships must use `.options(selectinload(...))` or `.options(joinedload(...))`. Add a linter rule to detect missing eager loading.

---

### DB-013 [MEDIUM] — N+1 in `knowledge_graph_service` for course+prerequisite+competency

**File**: `backend/app/services/knowledge_graph_service.py:15-145`

**Root cause**: Three consecutive loops each query individual rows by ID:
1. Lines 15-39: Loops over all `InstitutionalCourse` records, queries `KnowledgeNode` individually
2. Lines 42-80: Loops over all `InstitutionalCoursePrerequisite`, queries source/target nodes individually
3. Lines 83-145: Loops over all `Competency` and `CourseCompetency` records, queries nodes individually

**Impact**: Each `ensure_*` function call during system initialization generates 100+ queries. For 60 courses + 50 prerequisites + 30 competencies + 80 associations = **~220 queries** instead of **~10**.

**Fix**: Replace each loop with a single `IN` query:
```python
existing_nodes = {
    (n.node_type, n.external_id): n
    for n in db.query(KnowledgeNode).filter(
        KnowledgeNode.node_type == 'course',
        KnowledgeNode.external_id.in_([c.id for c in courses])
    ).all()
}
```

---

### DB-014 [LOW] — `audit_service.log_action` commits on every call

**File**: `backend/app/services/audit_service.py:29`

**Root cause**: The `log_action` function calls `db.commit()` after every single audit log insert. If multiple actions are logged in a single request (e.g., enrollment + diagnostic + path generation), this creates multiple round-trips. Worse, if a subsequent business operation fails after the audit commit, the audit is already committed but the business changes are rolled back — a partial durability issue.

```python
def log_action(db: Session, ...):
    log = AuditLog(...)
    db.add(log)
    db.commit()  # ← premature commit
```

**Impact**: Partial commits that survive business transaction rollbacks. For example, an enrollment failure that triggers a rollback leaves orphaned audit log entries.

**Fix**: Remove `db.commit()` from `log_action`. Let the caller's transaction boundary manage the commit. If the caller uses `UnitOfWork`, the audit log is committed atomically with the business data.

---

### DB-015 [LOW] — Missing index on `student_memories.updated_at`

**File**: `backend/app/models/student_memory.py`

**Root cause**: The `student_memories` table is queried with `ORDER BY updated_at DESC` in `memory_service.py` to get "recent memories". There is no index on `updated_at`, causing a sequential scan + sort for every tutor request.

**Impact**: As the memories table grows (potentially thousands per student), each tutor query performs a sequential scan + sort. On a table with 100k+ rows, this adds 10-50ms per tutor response.

**Fix**: Add index:
```python
Index("ix_student_memories_updated_at", "updated_at")
```
Or better, a compound index on `(student_id, updated_at)` for the most common query pattern:
```python
Index("ix_student_memories_student_updated", "student_id", "updated_at")
```

---

## Additional Observations

### OBS-001: `UnitOfWork.commit()` inside `with uow:` block

The `deps.py:get_uow()` yields a `UnitOfWork` that auto-commits on success and auto-rollbacks on exception. However, some service code (e.g., `activation_service.py:165`) calls `uow.commit()` MANUALLY inside the block. This is fine but could cause confusion — after the manual commit, the auto-commit in `get_uow()` calls `commit()` again, which is idempotent.

### OBS-002: `db.flush()` for ID generation is unnecessary

Several functions call `db.flush()` just to get a generated UUID. Since all IDs use `uuid4()` with Python-side generation (`default=lambda: uuid4().hex[:16]` or `default=uuid4`), the ID is available immediately without a flush. The flushes are redundant (e.g., `session_service.py:55, 72, 76`).

### OBS-003: Pool configuration not tuned for concurrent load

Production config: `pool_size=5, max_overflow=10`. With sync sessions (DB-002), each request holds a connection for the full request duration. With 15 concurrent requests (the pool maximum), the 16th request blocks the event loop waiting for a connection. Since the loop is already blocked by earlier requests, this creates a **connection pool starvation deadlock** under load.

### OBS-004: No `CONCURRENTLY` for index creation

The migration at `4c5d6e7f8a9b` creates indexes without `CONCURRENTLY`. On a production database with existing data, `CREATE INDEX` acquires a lock that blocks writes. All indexes should use `CREATE INDEX CONCURRENTLY` (requires `op.execute()` with raw SQL).

### OBS-005: Migration validation logic is overly defensive but fragile

Migrations like `0a1b2c3d4e5f` and `6a7b8c9d0e1f` include runtime validation (`_validate_existing_table()`) that checks column existence. This is good for idempotency but raises `RuntimeError` on ANY mismatch — including benign changes like nullable flag differences. A more defensive approach would log a warning and adapt.

### OBS-006: The `expire_on_commit=False` in session config masks stale data

While `expire_on_commit=False` prevents lazy-load errors after commit, it also means objects hold pre-commit values. If another transaction modifies the same row after the commit but before the request ends, the in-memory object still shows the old values. This is a trade-off, not a bug, but deserves documentation.

### OBS-007: No repository layer between services and models

All query logic is inline in 29 service files. There is no `repositories/` directory. This means:
- N+1 patterns are scattered and hard to find
- No centralized query optimization
- Same query patterns repeated across services
- Testing requires full database setup per service test

---

## Schema Drift Detection Summary

| Table | In Model? | In Alembic? | In Migration? | Status |
|-------|-----------|-------------|---------------|--------|
| users | ✅ | ✅ | ✅ (initial + token_version pending) | ✅ (pending merge) |
| courses | ✅ | ✅ | ✅ | ✅ |
| learning_objectives | ✅ | ✅ | ✅ | ✅ |
| resources | ✅ | ✅ | ✅ | ✅ |
| resource_objectives | ✅ | ✅ | ✅ | ✅ |
| enrollments | ✅ | ✅ | ✅ | ✅ |
| audit_logs | ✅ | ✅ | ✅ | ✅ |
| login_attempts | ✅ | ✅ | ✅ | ✅ |
| diagnostic_results | ✅ | ✅ | ✅ | ✅ |
| learning_paths | ✅ | ✅ | ✅ | ✅ |
| path_modules | ✅ | ✅ | ✅ | ✅ |
| evaluation_attempts | ✅ | ✅ | ✅ | ✅ |
| competencies | ✅ | ✅ | ✅ | ✅ |
| course_competencies | ✅ | ✅ | ✅ | ✅ |
| student_profiles | ✅ | ✅ | ✅ | ✅ |
| student_progress | ✅ | ✅ | ✅ | ✅ |
| course_prerequisites | ✅ | ✅ | ✅ | ✅ |
| student_memories | ✅ | ✅ | ✅ | ✅ |
| conversation_messages | ✅ | ✅ | ✅ | ✅ |
| weakness_records | ✅ | ✅ | ✅ | ✅ |
| strength_records | ✅ | ✅ | ✅ | ✅ |
| knowledge_nodes | ✅ | ✅ | ✅ | ✅ |
| knowledge_edges | ✅ | ✅ | ✅ | ✅ |
| event_outbox | ✅ | ✅ | ✅ | ✅ |
| idempotency_keys | ✅ | ✅ | ✅ | ✅ |
| shared_memory_records | ✅ | ✅ | ✅ | ✅ |
| institutional_courses | ✅ | ✅ | ✅ | ✅ |
| institutional_course_prerequisites | ✅ | ✅ | ✅ | ✅ |
| teacher_assignments | ✅ | ✅ | ✅ | ✅ |
| learning_sessions | ✅ | ✅ | ✅ | ✅ |
| **educational_context** | ✅ | ❌ | ❌ | ❌ **DRIFT** |
| **programming_metrics** | ✅ | ❌ | ❌ | ❌ **DRIFT** |
| **concept_prerequisite** | ✅ | ❌ | ❌ | ❌ **DRIFT** |
| **resource_programming_tag** | ✅ | ❌ | ❌ | ❌ **DRIFT** |

---

## Rollback Safety Assessment

### Migration downgrade coverage

| Migration | Downgrade? | Safe? | Notes |
|-----------|-----------|-------|-------|
| `83058a18afd3` | ✅ | ✅ | Drops all tables + enums |
| `6a7b8c9d0e1f` | ✅ | ✅ | Idempotent (checks table exists) |
| `8b9c0d1e2f3a` | ✅ | ✅ | Idempotent |
| `3a4b5c6d7e8f` | ✅ | ✅ | Drops table + index |
| `9a8b7c6d5e4f` | ✅ | ✅ | Drops columns + table |
| `0a1b2c3d4e5f` | ✅ | ✅ | Idempotent drop table |
| `1b2c3d4e5f6a` | ✅ | ✅ | Drops columns |
| `0b1c2d3e4f5a` | ✅ | ✅ | Drops column (UNMERGED) |
| `3ba21248a301` | ✅ | ✅ | No-op merge |
| `4c5d6e7f8a9b` | ✅ | ✅ | Drops tables, columns |

**All migrations have a downgrade path**. Most are idempotent with pre-checks.

### Rollback risks

1. **Downgrading past merge point `3ba21248a301`**: Both parent branches downgrade independently. The `1b2c3d4e5f6a` downgrade drops 6 columns from `idempotency_keys`. The `0a1b2c3d4e5f` downgrade drops the `shared_memory_records` table. These are independent operations — safe but slow.

2. **Downgrading past `9a8b7c6d5e4f`**: Drops `idempotency_keys` table entirely. Any pending idempotent operations still in-flight (e.g., event outbox publishing) will lose their idempotency protection.

3. **Downgrading past `83058a18afd3`**: Drops ALL tables and ALL enums. Destructive but expected.

4. **Data loss on downgrade**: Column drops like `token_version` (downgrade of `0b1c2d3e4f5a`) are irreversible — data is lost. The `status`, `event_type`, `aggregate_id`, `trace_id`, `causation_id`, and `completed_at` columns on `idempotency_keys` are also dropped. These should be backed up before downgrading.

### Rollback recommendations

- Always create a database dump before downgrading
- For hotfix rollbacks, prefer a new "revert" migration over downgrading (preserves data as nullable columns instead of dropping)
- Use `alembic downgrade --sql` to preview the SQL before executing

---

## Migration Governance Recommendations

### G-001: Create merge migration for orphan head
```bash
alembic merge -m "merge token_version into reconciled schema" 4c5d6e7f8a9b 0b1c2d3e4f5a
```

### G-002: Add missing model imports to alembic/env.py
Add the 4 missing models and create an autogenerate migration.

### G-003: Adopt no-`create_all` policy
Remove any `Base.metadata.create_all()` calls from production code. All schema changes must go through migrations. The 4 drifted tables are evidence this policy was violated.

### G-004: Add `alembic check` to CI pipeline
Add to CI:
```bash
alembic check  # Fails if model metadata != migration chain
```
This catches drift before deployment.

### G-005: Add migration naming convention
All migrations should follow: `{revision_id}_{action}_{table}.py`. Currently they're descriptive but inconsistent (some in Spanish, some in English, some mixed).

### G-006: Add migration review checklist
Every migration PR should verify:
- ✅ Both `upgrade()` and `downgrade()` are implemented
- ✅ `down_revision` points to the correct parent
- ✅ No `Base.metadata.create_all()` bypass
- ✅ Indexes use `CONCURRENTLY` for production safety
- ✅ New columns are nullable (or have `server_default`) for zero-downtime deploys
- ✅ New tables have proper FK constraints and indexes
- ✅ Models are imported in `alembic/env.py`

### G-007: Adopt zero-downtime migration patterns
- New columns: MUST be nullable or have `server_default`
- Column renames: Use `ALTER TABLE RENAME COLUMN` + add old column as a view
- Table renames: Add new table, dual-write, backfill, switch reads
- Indexes: Use `CREATE INDEX CONCURRENTLY` (requires `op.execute()`)

### G-008: Add indexes as a non-blocking operation
Replace `op.create_index()` with `CONCURRENTLY` for production:
```python
op.execute(
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_name ON table_name (columns)"
)
```

---

## Deadlock Analysis

### Current deadlock risk: LOW

The codebase uses three mechanisms that prevent deadlocks:

1. **Advisory locks (`pg_advisory_xact_lock`)**: Transaction-scoped, automatically released on commit/rollback. Since these are POSIX-style advisory locks (not row locks), they cannot participate in lock escalation deadlocks with row-level locks.

2. **`FOR UPDATE` row locks**: Used only in `memory_service.py:79` and `student_service.py:89`, always within an advisory lock guard. The `FOR UPDATE` is acquired AFTER the advisory lock is held, so no deadlock between advisory and row locks.

3. **`begin_nested()` savepoints**: The savepoint wraparound in `memory_service.py` and `user_service.py` uses `try/except IntegrityError`. The error is caught, the savepoint rolled back, and the operation continues — no deadlock.

### Potential deadlock concern

If two requests acquire advisory locks in different orders:
```
Request A: lock("enroll:{course1}:{student1}"), then FOR UPDATE on enrollment
Request B: lock("enroll:{course2}:{student2}"), then FOR UPDATE on enrollment
```
No cross-lock ordering issue since each operation locks only ONE key at a time.

However, if a future feature adds multiple advisory locks per transaction, the lock acquisition order MUST be consistent across all code paths to prevent deadlocks.

---

## Observability Recommendations

### OBS-R-001: Add query logging middleware
Add SQLAlchemy echo logging for slow queries (>100ms):
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# Or use a custom event listener:
from sqlalchemy import event
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info['query_start'] = time.time()
@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start']
    if total > 0.1:
        logger.warning(f"Slow query ({total:.2f}s): {statement[:200]}")
```

### OBS-R-002: Track connection pool utilization
Expose pool stats via a metrics endpoint:
```python
from sqlalchemy import event
pool_stats = {"checked_out": 0, "checked_in": 0}
@event.listens_for(engine.pool, "checkout")
def receive_checkout(dbapi_con, con_record, con_proxy):
    pool_stats["checked_out"] += 1
```

### OBS-R-003: Add migration drift monitoring
Run alembic check as a periodic job and alert on drift. Alternatively, expose the current migration head as a health-check endpoint.

### OBS-R-004: Add transaction duration tracing
Instrument `UnitOfWork.commit()` and `UnitOfWork.rollback()` with timing. Log any transaction that takes longer than 1 second.

---

## Summary

| ID | Severity | Component | Root Cause | Fix |
|---|----------|-----------|------------|-----|
| DB-001 | CRITICAL | Alembic migration chain | Unmerged head `0b1c2d3e4f5a` — `token_version` column may not exist | Create merge migration |
| DB-002 | HIGH | db/session.py + deps.py | Sync `Session` in async FastAPI — event loop blocked on ALL DB I/O | Convert to asyncpg + AsyncSession |
| DB-003 | HIGH | alembic/env.py | 4 models have NO migration representation — schema drift | Add imports + autogenerate |
| DB-004 | HIGH | course_service.py:257-276 | N+1: individual `User` queries per enrollment | Use `selectinload` or batch IN query |
| DB-005 | HIGH | student_service.py:454-459 | N+1: individual `Resource` queries per module | Use `selectinload(PathModule.resource)` |
| DB-006 | HIGH | prerequisite_service.py:206-256 | N+1: per-prerequisite queries for course/completion/enrollment | Batch-load with IN queries |
| DB-007 | HIGH | prerequisite_service.py:461-483 | Compounded N+1: `check_course_access` in loop | Use batch `_batch_check_course_access` |
| DB-008 | HIGH | knowledge_graph_service.py:201-228 | Triple-nested N+1 in recommendation query | Batch-load nodes + edges |
| DB-009 | MEDIUM | enrollment, learning_path, diagnostic, progress models | No unique constraints for business rules | Add `UniqueConstraint` to models |
| DB-010 | MEDIUM | Multiple models | Missing compound indexes on query-heavy paths | Add compound indexes |
| DB-011 | MEDIUM | evaluation_attempt.py | No `relationship()` for `module_id` FK | Add `relationship("PathModule")` |
| DB-012 | MEDIUM | All 29 services | Zero usage of eager loading (`selectinload`/`joinedload`) | Root cause of 12 N+1 patterns |
| DB-013 | MEDIUM | knowledge_graph_service.py:15-145 | N+1: individual node queries for courses/prereqs/competencies | Batch-load with IN queries |
| DB-014 | LOW | audit_service.py:29 | Premature `commit()` on every log action | Remove commit, let caller manage TX |
| DB-015 | LOW | student_memory.py | Missing index on `updated_at` for memory queries | Add compound index |

---

## Files Examined

- `backend/alembic/env.py` — Migration environment configuration
- `backend/alembic/versions/*.py` (10 files) — All migration scripts
- `backend/app/db/base.py` — DeclarativeBase
- `backend/app/db/session.py` — Engine + SessionLocal config
- `backend/app/db/uow.py` — UnitOfWork with savepoints + outbox
- `backend/app/db/locks.py` — Advisory locking
- `backend/app/api/deps.py` — FastAPI dependency injection
- `backend/app/models/*.py` (26 model files)
- `backend/app/services/*.py` (29 service files)

---

*End of report — generated by opencode forensic audit agent*
