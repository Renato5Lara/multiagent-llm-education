# DB-003: Schema Drift — 4 Models Have No Migration Representation

**Severity**: HIGH  
**Component**: Alembic migration tracking  
**Files**: `backend/alembic/env.py`, `backend/app/models/educational_context.py`, `backend/app/models/programming_metrics.py`, `backend/app/models/programming_prerequisite.py`, `backend/app/models/resource_programming_tag.py`  
**Status**: FIXED (env.py imports + migration `6d7e8f9a0b1c`)

---

## Root Cause

Four SQLAlchemy models were added to `Base` subclasses but were **never** imported in `alembic/env.py` and have **no corresponding migration file**:

| Model | Table | Missing Since |
|-------|-------|---------------|
| `EducationalContext` | `educational_context` | ~2026-05-23 |
| `ProgrammingMetrics` | `programming_metrics` | ~2026-05-23 |
| `ConceptPrerequisite` | `concept_prerequisite` | ~2026-05-23 |
| `ResourceProgrammingTag` | `resource_programming_tag` | ~2026-05-23 |

These tables exist only in code. If `Base.metadata.create_all()` was ever called during development, the tables exist locally but are completely invisible to Alembic.

## Impact

- Production deploy via `alembic upgrade head` — these tables are **never created**
- Any service code referencing these models crashes with `psycopg2.errors.UndefinedTable`
- Affected services: `activation_service.py`, `programming_metrics_service.py`, `programming_course_service.py`, `programming_pathway_service.py`
- `alembic check` passes because the env.py metadata doesn't include these tables

## Reproduction

```bash
# Verify drift: compare model tables vs migration tables
# 4 tables exist in models but NOT in any migration file
grep -c "educational_context\|programming_metrics\|concept_prerequisite\|resource_programming_tag" alembic/versions/*.py
# Returns 0 matches
```

## Fix Applied

### 1. Added imports to `alembic/env.py`
```python
from app.models.educational_context import EducationalContext
from app.models.programming_prerequisite import ConceptPrerequisite
from app.models.programming_metrics import ProgrammingMetrics
from app.models.resource_programming_tag import ResourceProgrammingTag
```

### 2. Created migration `6d7e8f9a0b1c`
Creates all 4 tables with proper columns, FKs, and indexes.

## Prevention

- G-003: No `Base.metadata.create_all()` in production code
- G-004: `alembic check` in CI pipeline
- G-006: Migration review checklist must verify all models are in env.py
