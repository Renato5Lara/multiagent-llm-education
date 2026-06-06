# DB-004 through DB-008, DB-012, DB-013: N+1 Query Patterns

**Severity**: HIGH (aggregate)  
**Component**: Service layer query patterns  
**Files**: `backend/app/services/*` (8 service files affected)  
**Status**: REPORTED

---

## Summary

**Zero usage** of `selectinload`, `joinedload`, `subqueryload`, or any `.options()` call across **29 service files**. All ~40 relationships use default `lazy='select'`. Every relationship access fires a separate SQL query.

Total active N+1 patterns: **12** in **8 service files**.

---

## Pattern Details

### N+1 per enrolled student (course_service.py:257-276)
```python
enrollments = db.query(Enrollment).filter(...).all()       # 1 query
for enrollment in enrollments:
    student = db.query(User).filter(User.id == enrollment.student_id).first()  # N queries
```
**Fix**: `selectinload(Enrollment.student)` or batch `User.id.in_(student_ids)`.

### N+1 per module (student_service.py:454-459)
```python
modules = db.query(PathModule).filter(...).all()
for mod in modules:
    if mod.resource_id:
        resource = db.query(Resource).filter(...).first()
```
**Fix**: `selectinload(PathModule.resource)`.

### N+1 per prerequisite (prerequisite_service.py:206-256)
```python
for prereq in prereq_inst_courses:
    prereq_course = db.query(Course).filter(...).first()   # query 1
    if not prereq_course:
        prereq_course = db.query(Course).filter(...).first() # query 2
    is_completed = has_student_completed_course(...)        # query 3
    is_enrolled = is_student_enrolled_in_course(...)        # query 4
```
**Fix**: Already has `_batch_check_course_access` — wire it into the single-course path.

### Compounded N+1 chain (prerequisite_service.py:461-483)
```python
for course in next_courses:
    access = check_course_access(db, student, course)  # +20 queries each
```
**Fix**: Switch to `_batch_check_course_access`.

### Triple-nested N+1 (knowledge_graph_service.py:201-228)
```python
for weakness in weaknesses:
    for node in weak_nodes:
        for edge in teaching_edges:
            course_node = db.query(...).first()
```
**Fix**: Batch-load all related nodes in single `IN` queries.

### Lazy load N+1 (programming_course_service.py:173-184)
```python
assocs = db.query(CourseCompetency).filter(...).all()
for a in assocs:
    competency = a.competency  # lazy load → N queries
```
**Fix**: `selectinload(CourseCompetency.competency)`.

### Triangular loops (knowledge_graph_service.py:15-145)
Three separate loops over all courses/prerequisites/competencies querying nodes individually.
**Fix**: Replace each loop with single `IN` query to `KnowledgeNode`.

---

## Root Cause

No eager loading infrastructure exists in the codebase. `selectinload`, `joinedload`, `subqueryload` are never imported or used.

**Resolution roadmap**:
1. Add `selectinload` to the top-5 hottest query paths (course_service, student_service, prerequisite_service)
2. Add `selectinload` to remaining medium-severity paths
3. Add a linter rule: `no-undefined-eager-load` — flag any loop that accesses relationships without eager loading
4. Convert all `lazy='select'` model relationships to explicit `lazy='selectin'` where the relationship is frequently accessed together with the parent
