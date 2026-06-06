# DB-009 + DB-010: Missing Unique Constraints and Compound Indexes

**Severity**: MEDIUM  
**Component**: SQLAlchemy models  
**Status**: REPORTED

---

## Missing Unique Constraints (DB-009)

| Table | Missing Constraint | Business Rule |
|-------|-------------------|---------------|
| `enrollments` | `(student_id, course_id)` | A student can be enrolled in the same course at most once |
| `learning_paths` | `(student_id, course_id)` | One learning path per student per course |
| `diagnostic_results` | `(student_id, course_id)` | One diagnostic result per student per course |
| `student_progress` | `(student_id, course_id, resource_id)` | One progress entry per resource per enrollment |

**Impact**: Advisory locks (`pg_advisory_xact_lock`) prevent races within a single instance but fail under horizontal scaling. Direct DB modifications bypass the lock entirely.

## Missing Compound Indexes (DB-010)

| Table | Missing Index | Query Pattern |
|-------|---------------|---------------|
| `enrollments` | `(student_id, status)` | Dashboard: my active enrollments |
| `learning_paths` | `(student_id, course_id)` | get_learning_path_detail |
| `path_modules` | `(path_id, status)` | Module progress aggregation |
| `student_progress` | `(student_id, course_id)` | Course progress aggregation |
| `diagnostic_results` | `(student_id, course_id)` | Get diagnostic by student + course |
| `audit_logs` | `(user_id, entity_type, entity_id)` | Admin audit log queries |
| `conversation_messages` | `(student_id, course_id)` | Tutor context loading |

**Impact**: Sequential scans on tables that grow with usage. Single-column indexes force `BitmapAnd` scans. Performance degrades as tables exceed 10k rows.

## Migration Implementation

```python
"""add missing unique constraints and compound indexes"""

def upgrade():
    # Unique constraints
    op.create_unique_constraint("uq_enrollment_student_course", "enrollments", ["student_id", "course_id"])
    op.create_unique_constraint("uq_learning_path_student_course", "learning_paths", ["student_id", "course_id"])
    op.create_unique_constraint("uq_diagnostic_student_course", "diagnostic_results", ["student_id", "course_id"])
    op.create_unique_constraint("uq_student_progress_student_course_resource", "student_progress", ["student_id", "course_id", "resource_id"])

    # Compound indexes
    op.create_index("ix_enrollment_student_status", "enrollments", ["student_id", "status"])
    op.create_index("ix_learning_path_student_course", "learning_paths", ["student_id", "course_id"])
    op.create_index("ix_path_module_path_status", "path_modules", ["path_id", "status"])
    op.create_index("ix_student_progress_student_course", "student_progress", ["student_id", "course_id"])
    op.create_index("ix_diagnostic_student_course", "diagnostic_results", ["student_id", "course_id"])
    op.create_index("ix_audit_log_user_entity", "audit_logs", ["user_id", "entity_type", "entity_id"])
```
