# DB-001: Unmerged Migration Head — `token_version` Column May Not Exist

**Severity**: CRITICAL  
**Component**: Alembic migration chain  
**File**: `backend/alembic/versions/0b1c2d3e4f5a_add_token_version_to_users.py`  
**Status**: FIXED (merge migration `5c924adef43d` created)

---

## Root Cause

Migration `0b1c2d3e4f5a` adds the `token_version` column to `users` for refresh token rotation. It branched from `9a8b7c6d5e4f`, the same parent as two other branches (`0a1b2c3d4e5f` and `1b2c3d4e5f6a`). The merge migration `3ba21248a301` only merged the latter two, **excluding** `0b1c2d3e4f5a`.

**Result**: Two alembic heads — `4c5d6e7f8a9b` (HEAD 1) and `0b1c2d3e4f5a` (HEAD 2). `alembic upgrade head` applies only one.

## Impact

- `alembic upgrade head` applies only ONE head
- If HEAD 1 is applied first: `token_version` column is NEVER created
- `User.token_version` references a column that may not exist → `OperationalError`
- All token refresh operations in `auth_service.py` fail
- `alembic check` reports "2 heads" but CI may not run it

## Reproduction

```bash
alembic history
# Two heads: 4c5d6e7f8a9b (head), 0b1c2d3e4f5a (head)
alembic upgrade head
# Applies only one head — silent partial upgrade
```

## Fix Applied

Created merge migration `5c924adef43d`:
```bash
alembic merge -m "merge token_version into reconciled schema" 4c5d6e7f8a9b 0b1c2d3e4f5a
```

New chain:
```
9a8b7c6d5e4f → (0a1b2c3d4e5f + 1b2c3d4e5f6a) → 3ba21248a301 → 4c5d6e7f8a9b
                                                                  ↘
9a8b7c6d5e4f → 0b1c2d3e4f5a ─────────────────────────────────────→ 5c924adef43d (single head)
```

## Prevention

- Add `alembic check` to CI pipeline
- Migration PR checklist must verify single head
