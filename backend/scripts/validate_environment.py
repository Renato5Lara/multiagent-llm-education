#!/usr/bin/env python3
"""
validate_environment.py — UPAO-MAS-EDU Environment Validator.

Validates all system components are correctly configured and running.
Exits with 0 if all checks pass, 1 if any check fails.

Usage:
    python scripts/validate_environment.py
    python scripts/validate_environment.py --verbose
"""

import argparse
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path


def check(description: str, condition: bool, fix: str = "") -> bool:
    if condition:
        print(f"  ✅ {description}")
        return True
    print(f"  ❌ {description}")
    if fix:
        print(f"     ⚠  Fix: {fix}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate UPAO-MAS-EDU environment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    args = parser.parse_args()
    verbose = args.verbose

    root = Path(__file__).resolve().parent.parent.parent
    backend = root / "backend"
    frontend = root / "frontend"

    all_ok = True
    total = 0
    passed = 0

    def run_check(desc: str, ok: bool, fix: str = ""):
        nonlocal total, passed, all_ok
        total += 1
        if ok:
            passed += 1
        else:
            all_ok = False
        check(desc, ok, fix)

    header = f"\n{'='*60}\n  UPAO-MAS-EDU Environment Validator v1.0.0\n{'='*60}\n"
    print(header)

    # ── 1. Python ────────────────────────────────────────────────
    print("\n📦 Python Environment")
    py_version = sys.version_info
    run_check(
        f"Python 3.12+ (found {py_version.major}.{py_version.minor}.{py_version.micro})",
        py_version.major >= 3 and py_version.minor >= 12,
        "Install Python 3.12+ from https://python.org",
    )

    # ── 2. Dependencies ──────────────────────────────────────────
    print("\n📚 Dependencies")
    req_file = backend / "requirements.lock"
    req_exists = req_file.exists()
    run_check(f"requirements.lock exists at {req_file}", req_exists)
    if req_exists and verbose:
        print(f"     File: {req_file}")

    # Check key packages
    core_packages = [
        "fastapi", "sqlalchemy", "pydantic", "uvicorn",
        "alembic", "langgraph", "pytest", "httpx",
    ]
    for pkg in core_packages:
        try:
            ver = importlib.metadata.version(pkg)
            if verbose:
                print(f"     {pkg}=={ver}")
            run_check(f"Package installed: {pkg}", True)
        except importlib.metadata.PackageNotFoundError:
            run_check(f"Package installed: {pkg}", False, f"pip install {pkg}")

    # ── 3. Environment File ──────────────────────────────────────
    print("\n🔧 Configuration")
    env_file = backend / ".env"
    run_check(
        f".env file exists at {env_file}",
        env_file.exists(),
        f"cp {backend}/.env.example {env_file} && edit credentials",
    )
    env_example = backend / ".env.example"
    run_check(
        f".env.example exists at {env_example}",
        env_example.exists(),
    )

    # ── 4. Database ──────────────────────────────────────────────
    print("\n🗄️  Database")
    try:
        from app.core.config import settings
        db_url = settings.DATABASE_URL
        run_check("DATABASE_URL configured", bool(db_url))
        if verbose:
            sanitized = db_url.split("@")[-1] if "@" in db_url else db_url
            print(f"     Host: {sanitized}")

        from sqlalchemy import create_engine, text
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        run_check("Database connection OK", True)
        engine.dispose()

        async def check_async():
            from sqlalchemy.ext.asyncio import create_async_engine
            async_url = settings.DATABASE_URL.replace(
                "+psycopg", "+asyncpg"
            ).replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            async_engine = create_async_engine(async_url)
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await async_engine.dispose()

        import asyncio
        asyncio.run(check_async())
        run_check("Async database connection OK", True)
    except Exception as e:
        run_check(
            "Database connection",
            False,
            f"Start PostgreSQL: docker compose up -d postgres. Error: {e}",
        )

    # ── 5. Alembic Migrations ────────────────────────────────────
    print("\n🔄 Migrations")
    try:
        result = subprocess.run(
            ["alembic", "current"],
            cwd=backend,
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            current = result.stdout.strip()
            run_check(f"Migrations: {current}", True)
        else:
            run_check("Alembic migrations", False, "Run: alembic upgrade head")
    except FileNotFoundError:
        run_check("Alembic installed", False, "pip install alembic")
    except subprocess.TimeoutExpired:
        run_check("Alembic check timed out", False)

    # ── 6. Seed Data ─────────────────────────────────────────────
    print("\n🌱 Seed Data")
    try:
        from app.db.session import SessionLocal
        from app.models.user import User
        session = SessionLocal()
        user_count = session.query(User).count()
        session.close()
        run_check(
            f"Seed data loaded ({user_count} users)",
            user_count >= 4,
            "Run: python seed.py",
        )
    except Exception as e:
        run_check("Seed data", False, f"Run: python seed.py. Error: {e}")

    # ── 7. Upload Directory ──────────────────────────────────────
    print("\n📁 Upload Directories")
    upload_dirs = ["uploads/courses", "uploads/resources", "uploads/images", "uploads/temp"]
    upload_base = backend / "uploads"
    for d in upload_dirs:
        p = backend / d
        run_check(f"Upload dir: {d}", p.exists() or p.is_dir() or upload_base.exists())

    # ── 8. JWT ───────────────────────────────────────────────────
    print("\n🔑 JWT Configuration")
    try:
        from app.core.config import settings
        run_check(
            "SECRET_KEY configured",
            settings.SECRET_KEY != "cambia-esto-en-produccion-genera-uno-aleatorio-de-32-bytes",
            "Generate a random SECRET_KEY",
        )
        run_check(f"ALGORITHM: {settings.ALGORITHM}", settings.ALGORITHM == "HS256")
        run_check(f"ACCESS_TOKEN_EXPIRE: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}min", True)
    except Exception as e:
        run_check("JWT config", False, str(e))

    # ── 9. LLM API Keys ──────────────────────────────────────────
    print("\n🤖 LLM Configuration")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    has_llm = bool(openai_key or anthropic_key)
    run_check(
        "LLM API key configured (OpenAI or Anthropic)",
        has_llm,
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env",
    )

    # ── 10. Tavily ───────────────────────────────────────────────
    print("\n🔍 Tavily Search")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    run_check(
        "TAVILY_API_KEY configured (optional)",
        bool(tavily_key),
    )

    # ── 11. Frontend ─────────────────────────────────────────────
    print("\n🎨 Frontend")
    node_modules = frontend / "node_modules"
    run_check(
        "Frontend dependencies installed",
        node_modules.exists(),
        "cd frontend && npm ci",
    )
    pkg_json = frontend / "package.json"
    run_check("Frontend package.json exists", pkg_json.exists())
    dist_dir = frontend / "dist"
    run_check(
        "Frontend production build exists",
        dist_dir.exists(),
        "cd frontend && npm run build",
    )

    # ── 12. Docker ───────────────────────────────────────────────
    print("\n🐳 Docker")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        run_check(
            f"Docker: {result.stdout.strip()}" if result.returncode == 0 else "Docker",
            result.returncode == 0,
            "Install Docker from https://docker.com",
        )
    except FileNotFoundError:
        run_check("Docker installed", False, "Install Docker from https://docker.com")

    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, text=True, timeout=10,
        )
        run_check(
            f"Docker Compose: {result.stdout.strip()}" if result.returncode == 0 else "Docker Compose",
            result.returncode == 0,
            "Docker Compose is included with Docker Desktop",
        )
    except FileNotFoundError:
        run_check("Docker Compose installed", False)

    # ── 13. Tests ────────────────────────────────────────────────
    print("\n🧪 Tests")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_propagation_ttl.py", "-q"],
            cwd=backend,
            capture_output=True, text=True, timeout=60,
        )
        output = result.stdout.strip()
        if "passed" in output and "failed" not in output:
            run_check(f"Propagation TTL tests: {output}", True)
        else:
            run_check(f"Propagation TTL tests: {output}", False)
    except subprocess.TimeoutExpired:
        run_check("Tests timed out", False)
    except Exception as e:
        run_check("Tests", False, str(e))

    # ── 14. Version ──────────────────────────────────────────────
    print("\n🏷️  Version")
    try:
        from app.core.config import settings
        run_check(
            f"APP_NAME: {settings.APP_NAME}",
            settings.APP_NAME == "UPAO-MAS-EDU",
        )
        run_check(
            f"APP_VERSION: {settings.APP_VERSION}",
            settings.APP_VERSION == "1.0.0",
        )
    except Exception:
        pass

    # ── Summary ──────────────────────────────────────────────────
    summary = f"""
{'='*60}
  RESULTS: {passed}/{total} checks passed
{'='*60}
"""
    print(summary)

    if all_ok:
        print("  ✅ Environment is ready for release.\n")
        return 0
    else:
        print(f"  ❌ {total - passed} check(s) failed. Review fixes above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
