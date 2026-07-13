from snowflake.snowpark.context import get_active_session
from pathlib import Path
import re
import sys
import importlib.util


session = get_active_session()


sys.dont_write_bytecode = True


# ============================================================
# CONFIG
# ============================================================

DATABASE = "CICD_AUTOMATION_DEV"
SCHEMAS = [
     "PATIENTS", 
    "UTILITIES", "HOSPITALS"
]

TARGET_DB = "CICD_AUTOMATION{{env_suffix}}"

SYSTEM_OWNERS = {"SYSTEM", "SNOWFLAKE", "ACCOUNTADMIN", "ORGADMIN"}

# ============================================================
# PATH SETUP
# ============================================================

CURRENT_DIR = Path.cwd()
BASE_DIR = CURRENT_DIR.parent

TARGET_ROOT = BASE_DIR / "Projects" / "DDL"
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

print("DDL ROOT:", TARGET_ROOT)

# ============================================================
# FOLDER MAP
# ============================================================

FOLDER_MAP = {
    "TABLE": "tables",
    "DYNAMIC TABLE": "dynamic_tables",
    "VIEW": "views",
    "STAGE": "stages",
    "FILE FORMAT": "file_formats",
    "STREAM": "streams",
    "TASK": "tasks",
    "PROCEDURE": "procedures",
    "FUNCTION": "functions"
}

# ============================================================
# HELPERS
# ============================================================

def safe_query(sql):
    try:
        return session.sql(sql).collect()
    except Exception:
        return []


def replace_env(text):
    if not text:
        return text
    return re.sub(rf"\b{DATABASE}\b", TARGET_DB, text, flags=re.IGNORECASE)


def get_path(obj_type, name, schema):
    folder = FOLDER_MAP.get(obj_type, "others")
    path = TARGET_ROOT / schema / folder
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{name}.sql"


def fq(name, schema):
    return f"{TARGET_DB}.{schema}.{name}"

# ============================================================
# SYSTEM FILTER
# ============================================================

def is_system_procedure(row):
    owner = (row.get("OWNER") or "").upper()
    name = (row.get("PROCEDURE_NAME") or "").upper()
    catalog = (row.get("PROCEDURE_CATALOG") or "").upper()
    is_builtin = (row.get("IS_BUILTIN") or "").upper()

    if owner in SYSTEM_OWNERS:
        return True

    if name.startswith(("SYSTEM$", "SNOWFLAKE$", "$")):
        return True

    if is_builtin == "YES":
        return True

    if catalog and catalog != DATABASE.upper():
        return True

    return False

# ============================================================
# STAGE DDL (custom)
# ============================================================

def stage_ddl(name, schema):
    rows = safe_query(f"SHOW STAGES IN SCHEMA {DATABASE}.{schema}")

    for r in rows:
        row = {k.lower(): v for k, v in r.asDict().items()}

        if row.get("name") != name:
            continue

        ddl = [f"CREATE OR REPLACE STAGE {fq(name, schema)}"]

        if row.get("url"):
            ddl.append(f"URL = '{row['url']}'")
            if row.get("storage_integration"):
                ddl.append(f"STORAGE_INTEGRATION = {row['storage_integration']}")
        else:
            ddl.append("DIRECTORY = ( ENABLE = TRUE )")

        if row.get("comment"):
            ddl.append(f"COMMENT = '{row['comment']}'")

        return "\n".join(ddl)

    return f"-- FAILED STAGE {name}"

# ============================================================
# GET DDL CORE (FIXED)
# ============================================================

def get_ddl(obj_type, schema, name, signature=None):
    try:
        if obj_type == "STAGE":
            return stage_ddl(name, schema)

        if obj_type == "PROCEDURE":
            if not signature:
                return f"-- SKIPPED PROCEDURE {name}: missing signature"

            identifier = f"{DATABASE}.{schema}.{name}{signature}"

        else:
            identifier = f"{DATABASE}.{schema}.{name}"

        ddl = session.sql(f"SELECT GET_DDL('{obj_type}', '{identifier}')").collect()[0][0]
        return replace_env(ddl)

    except Exception as e:
        return f"-- FAILED {obj_type} {name}: {e}"

# ============================================================
# COLLECT OBJECTS
# ============================================================

objects = []

for schema in SCHEMAS:
    print(f"\nProcessing schema: {schema}")

    # ---------------- DYNAMIC TABLES ----------------
    dyn = safe_query(f"SHOW DYNAMIC TABLES IN SCHEMA {DATABASE}.{schema}")
    dyn_names = set()

    for r in dyn:
        objects.append((schema, r["name"], "DYNAMIC TABLE", None))
        dyn_names.add(r["name"])

    # ---------------- TABLES ----------------
    for r in safe_query(f"SHOW TABLES IN SCHEMA {DATABASE}.{schema}"):
        if r["name"] not in dyn_names:
            objects.append((schema, r["name"], "TABLE", None))

    # ---------------- VIEWS ----------------
    for r in safe_query(f"SHOW VIEWS IN SCHEMA {DATABASE}.{schema}"):
        objects.append((schema, r["name"], "VIEW", None))

    # ---------------- STAGES ----------------
    for r in safe_query(f"SHOW STAGES IN SCHEMA {DATABASE}.{schema}"):
        objects.append((schema, r["name"], "STAGE", None))

    # ---------------- FILE FORMATS ----------------
    for r in safe_query(f"SHOW FILE FORMATS IN SCHEMA {DATABASE}.{schema}"):
        objects.append((schema, r["name"], "FILE FORMAT", None))

    # ---------------- STREAMS ----------------
    for r in safe_query(f"SHOW STREAMS IN SCHEMA {DATABASE}.{schema}"):
        objects.append((schema, r["name"], "STREAM", None))

    # ---------------- TASKS ----------------
    for r in safe_query(f"SHOW TASKS IN SCHEMA {DATABASE}.{schema}"):
        objects.append((schema, r["name"], "TASK", None))

    # ========================================================
    # PROCEDURES (FIXED - INFORMATION_SCHEMA)
    # ========================================================

    proc_rows = safe_query(f"""
        SELECT *
        FROM {DATABASE}.INFORMATION_SCHEMA.PROCEDURES
        WHERE PROCEDURE_SCHEMA = '{schema}'
    """)

    for r in proc_rows:
        row = {k.upper(): v for k, v in r.asDict().items()}

        if is_system_procedure(row):
            continue

        name = row["PROCEDURE_NAME"]
        signature = row.get("ARGUMENT_SIGNATURE")  # ✅ CLEAN FIX

        objects.append((schema, name, "PROCEDURE", signature))

# ============================================================
# WRITE OUTPUT
# ============================================================

print("\nTOTAL OBJECTS:", len(objects))

for item in objects:
    schema, name, obj_type, signature = item

    ddl = get_ddl(obj_type, schema, name, signature)
    file_path = get_path(obj_type, name, schema)

    try:
        file_path.write_text(ddl, encoding="utf-8")
        print(f"WROTE {schema} {obj_type}: {file_path}")

    except Exception as e:
        print(f"FAILED {schema} {obj_type} {name}: {e}")

print("DONE")