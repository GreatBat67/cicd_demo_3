import sys
from pathlib import Path
import importlib.util

sys.dont_write_bytecode = True

# ============================================================
# SAFE BASE DIR
# ============================================================

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

# ============================================================
# SQL FILES
# ============================================================

PHASE1_SQL_OUTPUT = (
    BASE_DIR.parent / "logs" / "create_databases_and_grants.sql"
)

CREATE_DCM_PROJECTS_SQL = (
    BASE_DIR.parent / "logs" / "create_dcm_projects.sql"
)

# ============================================================
# SQL EXECUTION (Snowpark ONLY)
# ============================================================

def execute_sql_file(sql_path: Path, session):

    if session is None:
        print(" No Snowpark session available")
        return False

    if not sql_path.exists():
        print(f" Missing SQL file: {sql_path}")
        return False

    sql_text = sql_path.read_text(encoding="utf-8")

    statements = []
    buffer = []

    for line in sql_text.splitlines():
        if line.strip().startswith("--"):
            continue

        buffer.append(line)

        if ";" in line:
            statements.append("\n".join(buffer).strip())
            buffer = []

    if buffer:
        statements.append("\n".join(buffer).strip())

    executed, errors = 0, 0

    for stmt in statements:
        stmt_clean = "\n".join(
            [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        ).strip()

        if not stmt_clean:
            continue

        try:
            session.sql(stmt_clean).collect()
            executed += 1
        except Exception as e:
            errors += 1
            print(f"⚠ SQL error: {str(e)[:120]}")
            print(f"   STMT: {stmt_clean[:120]}...")

    print(f"✔ SQL Executed: {executed}, Errors: {errors}")
    return errors == 0


# ============================================================
# RUN PYTHON SCRIPT (NO SUBPROCESS)
# ============================================================

def run_python_script(script_path: Path):

    spec = importlib.util.spec_from_file_location(
        script_path.stem,
        script_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


# ============================================================
# PIPELINE CONFIG (UPDATED)
# ============================================================

execution_order = [
    {
        "phase": "PHASE 1: INFRASTRUCTURE",
        "scripts": [
            BASE_DIR / "generate_db_schema.py",
            BASE_DIR / "dcm_project.py",
        ],
        "post_sql": [
            PHASE1_SQL_OUTPUT,
            CREATE_DCM_PROJECTS_SQL,
        ],
    },
    {
        "phase": "PHASE 2: DCM SETUP",
        "scripts": [
            BASE_DIR / "dcm" / "manifest.py",
            BASE_DIR / "dcm" / "dcm_files.py",
            BASE_DIR / "dcm" / "dcm_macros.py",
        ],
    },
    {
        "phase": "PHASE 3: DDL EXTRACTION",
        "scripts": [
            BASE_DIR / "ddl_scripts.py",
        ],
    },
]


# ============================================================
# PIPELINE RUNNER
# ============================================================

def run_pipeline(phases=None, skip_missing=True, stop_on_error=False):

    total = passed = failed = skipped = 0

    print("=" * 60)
    print("DCM PIPELINE (PY + SQL FIXED)")
    print("=" * 60)

    # --------------------------------------------------------
    # GET SNOWPARK SESSION ONCE
    # --------------------------------------------------------
    session = None
    try:
        from snowflake.snowpark.context import get_active_session
        session = get_active_session()
        print("✔ Snowpark session active")
    except Exception as e:
        print(f" No Snowpark session: {e}")

    for idx, phase in enumerate(execution_order):

        if phases is not None and idx not in phases:
            continue

        print("\n" + "=" * 60)
        print(phase["phase"])
        print("=" * 60)

        # ----------------------------
        # RUN PY SCRIPTS
        # ----------------------------
        for script in phase["scripts"]:
            total += 1

            if not script.exists():
                skipped += 1
                print(f"SKIP: {script.name}")
                continue

            print(f"\nRUNNING PY: {script.name}")

            try:
                run_python_script(script)
                passed += 1
                print("✔ DONE")

            except Exception as e:
                failed += 1
                print(f"✗ FAILED: {script.name}")
                print(str(e)[:500])

                if stop_on_error:
                    return False

        # ----------------------------
        # RUN POST SQL (NEW FEATURE)
        # ----------------------------
        for sql_file in phase.get("post_sql", []):
            sql_file = Path(sql_file)

            print(f"\nRUNNING SQL: {sql_file.name}")

            try:
                ok = execute_sql_file(sql_file, session)

                if ok:
                    print("✔ SQL DONE")
                else:
                    print("⚠ SQL FAILED")

            except Exception as e:
                failed += 1
                print(f"✗ SQL ERROR: {sql_file.name}")
                print(str(e)[:500])

                if stop_on_error:
                    return False


    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Total:   {total}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}")
    print("=" * 60)

    return failed == 0


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--phase", type=str, default=None)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--no-skip", action="store_true")

    args, _ = parser.parse_known_args()

    phases = None
    if args.phase:
        phases = [int(x.strip()) for x in args.phase.split(",")]

    success = run_pipeline(
        phases=phases,
        skip_missing=not args.no_skip,
        stop_on_error=args.stop_on_error,
    )

    sys.exit(0 if success else 1)