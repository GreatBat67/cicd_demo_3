from snowflake.snowpark.context import get_active_session
from pathlib import Path
import sys
import re

session = get_active_session()

sys.dont_write_bytecode = True

# ============================================================
# LOAD CONFIGURATION
# ============================================================

ROOT = Path.cwd().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.config import config

# ============================================================
# CONFIG
# ============================================================

PROJECT_NAME = config.project["name"]
DATABASES = config.databases
SCHEMAS = config.schemas

DATABASE = DATABASES[0]["name"]
TARGET_DB = "{{ database }}"

SYSTEM_OWNERS = {"SYSTEM", "SNOWFLAKE", "ACCOUNTADMIN", "ORGADMIN"}

# ============================================================
# OBJECT TYPE REGISTRY
# Drives folder creation, SHOW commands, and definition generation.
# ============================================================

OBJECT_REGISTRY = [
    # (object_type, folder_name, show_command_template, uses_get_ddl, get_ddl_type_override)
    ("DYNAMIC TABLE",     "dynamic_tables",      "SHOW DYNAMIC TABLES IN SCHEMA {fqn}",     True,  None),
    ("TABLE",             "tables",              "SHOW TABLES IN SCHEMA {fqn}",              True,  None),
    ("VIEW",              "views",               "SHOW VIEWS IN SCHEMA {fqn}",               True,  None),
    ("MATERIALIZED VIEW", "materialized_views",  "SHOW MATERIALIZED VIEWS IN SCHEMA {fqn}",  True,  None),
    ("EXTERNAL TABLE",    "external_tables",     "SHOW EXTERNAL TABLES IN SCHEMA {fqn}",     True,  None),
    ("STAGE",             "stages",              "SHOW STAGES IN SCHEMA {fqn}",              False, None),
    ("STREAM",            "streams",             "SHOW STREAMS IN SCHEMA {fqn}",             False, None),
    ("TASK",              "tasks",               "SHOW TASKS IN SCHEMA {fqn}",               True,  None),
    ("FILE FORMAT",       "file_formats",        "SHOW FILE FORMATS IN SCHEMA {fqn}",        False, None),
    ("PROCEDURE",         "stored_procedures",   None,                                       True,  None),
    ("FUNCTION",          "functions",           "SHOW USER FUNCTIONS IN SCHEMA {fqn}",      True,  None),
    ("PIPE",              "pipes",               "SHOW PIPES IN SCHEMA {fqn}",               True,  None),
    ("SEQUENCE",          "sequences",           "SHOW SEQUENCES IN SCHEMA {fqn}",           False, None),
    ("MASKING POLICY",    "masking_policies",    "SHOW MASKING POLICIES IN SCHEMA {fqn}",    True,  "MASKING_POLICY"),
    ("ROW ACCESS POLICY", "row_access_policies", "SHOW ROW ACCESS POLICIES IN SCHEMA {fqn}", True, "ROW_ACCESS_POLICY"),
    ("TAG",               "tags",               "SHOW TAGS IN SCHEMA {fqn}",                True,  None),
    ("ALERT",             "alerts",             "SHOW ALERTS IN SCHEMA {fqn}",              True,  None),
]

# Build FOLDER_MAP from registry
FOLDER_MAP = {obj_type: folder for obj_type, folder, *_ in OBJECT_REGISTRY}
FOLDER_MAP["OTHER"] = "others"

# ============================================================
# LOCATE PROJECT DIRECTORY
# ============================================================

project_name_lower = PROJECT_NAME.lower()
current = Path.cwd().resolve()

project_dir = None
for parent in [current] + list(current.parents):
    for child in parent.iterdir():
        if child.is_dir() and child.name.lower() == project_name_lower:
            project_dir = child.resolve()
            break
    if project_dir:
        break

if project_dir is None:
    raise RuntimeError(f"Could not locate project directory '{PROJECT_NAME}'.")

TARGET_ROOT = project_dir / "sources" / "definitions"
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print(f"Project       : {PROJECT_NAME}")
print(f"Source DB     : {DATABASE}")
print(f"Schemas       : {', '.join(SCHEMAS)}")
print(f"Definitions   : {TARGET_ROOT}")
print("=" * 60)

# ============================================================
# HELPERS
# ============================================================

def fq(name, schema):
    return f"{TARGET_DB}.{schema}.{name}"


def replace_env(text):
    if not text:
        return text
    return re.sub(rf"\b{DATABASE}\b", TARGET_DB, text, flags=re.IGNORECASE)


def get_path(obj_type, object_name, schema):
    folder = FOLDER_MAP.get(obj_type, "others")
    folder_path = TARGET_ROOT / schema / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path / f"{object_name}.sql"


def is_system_procedure(row, database, current_schema):
    owner = (row.get("PROCEDURE_OWNER") or "").upper()
    name = (row.get("PROCEDURE_NAME") or "").upper()
    catalog = (row.get("PROCEDURE_CATALOG") or "").upper()
    schema_name = (row.get("PROCEDURE_SCHEMA") or "").upper()
    is_builtin = (row.get("IS_BUILTIN") or "").upper()

    if owner in SYSTEM_OWNERS:
        return True
    if name.startswith(("SYSTEM$", "SNOWFLAKE$", "$")):
        return True
    if is_builtin == "Y":
        return True
    if catalog and catalog != database.upper():
        return True
    if schema_name and schema_name != current_schema.upper():
        return True
    return False


# ============================================================
# DEFINITION GENERATORS
# ============================================================

def generic_ddl_define(obj_type, name, schema, ddl_type=None):
    """Generic handler for any object type that supports GET_DDL."""
    ddl_key = ddl_type or obj_type
    try:
        ddl = session.sql(
            f"SELECT GET_DDL('{ddl_key}', '{DATABASE}.{schema}.{name}')"
        ).collect()[0][0]

        ddl = replace_env(ddl)

        # Normalize type name for regex (e.g. "ROW ACCESS POLICY" -> "ROW\s+ACCESS\s+POLICY")
        type_pattern = r"\s+".join(re.escape(w) for w in obj_type.split())
        ddl = re.sub(
            rf"CREATE\s+(OR\s+REPLACE\s+)?{type_pattern}\s+[^\s(]+",
            f"DEFINE {obj_type} {fq(name, schema)}",
            ddl,
            count=1,
            flags=re.IGNORECASE,
        )
        return ddl

    except Exception as e:
        return f"-- FAILED {obj_type} {fq(name, schema)} : {e}"


def stage_define(name, schema):
    try:
        rows = session.sql(f"SHOW STAGES IN SCHEMA {DATABASE}.{schema}").collect()
        for r in rows:
            row = {k.lower(): v for k, v in r.asDict().items()}
            if row.get("name") != name:
                continue

            lines = [f"DEFINE STAGE {fq(name, schema)}"]
            if row.get("url"):
                lines.append(f"URL = '{row['url']}'")
                if row.get("storage_integration"):
                    lines.append(f"STORAGE_INTEGRATION = {row['storage_integration']}")
            else:
                lines.append("DIRECTORY = ( ENABLE = TRUE )")
            if row.get("comment"):
                lines.append(f"COMMENT = '{row['comment']}'")
            return "\n".join(lines)

        return f"-- FAILED STAGE {fq(name, schema)}"
    except Exception as e:
        return f"-- FAILED STAGE {fq(name, schema)} : {e}"


def stream_define(name, schema):
    try:
        rows = session.sql(f"SHOW STREAMS IN SCHEMA {DATABASE}.{schema}").collect()
        for r in rows:
            if r["name"] == name:
                table_name = r.get("table_name", "")
                return f"DEFINE STREAM {fq(name, schema)}\nAS\nSELECT *\nFROM {replace_env(table_name)}"
        return f"-- FAILED STREAM {fq(name, schema)}"
    except Exception as e:
        return f"-- FAILED STREAM {fq(name, schema)} : {e}"


def sequence_define(name, schema):
    try:
        rows = session.sql(f"SHOW SEQUENCES IN SCHEMA {DATABASE}.{schema}").collect()
        for r in rows:
            row = {k.lower(): v for k, v in r.asDict().items()}
            if row.get("name") != name:
                continue
            lines = [f"DEFINE SEQUENCE {fq(name, schema)}"]
            if row.get("interval"):
                lines.append(f"INCREMENT = {row['interval']}")
            return "\n".join(lines)
        return f"-- FAILED SEQUENCE {fq(name, schema)}"
    except Exception as e:
        return f"-- FAILED SEQUENCE {fq(name, schema)} : {e}"


def file_format_define(name, schema):
    """File formats need GET_DDL but a slightly different regex pattern."""
    try:
        ddl = session.sql(
            f"SELECT GET_DDL('FILE FORMAT', '{DATABASE}.{schema}.{name}')"
        ).collect()[0][0]
        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?FILE\s+FORMAT\s+[^\s]+",
            f"DEFINE FILE FORMAT {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE,
        )
        return ddl
    except Exception as e:
        return f"-- FAILED FILE FORMAT {fq(name, schema)} : {e}"


def procedure_define(name, schema, signature="()"):
    """Procedures need signature in the GET_DDL call."""
    try:
        ddl = session.sql(
            f"SELECT GET_DDL('PROCEDURE', '{DATABASE}.{schema}.{name}{signature}')"
        ).collect()[0][0]
        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\s+[^\s(]+",
            f"DEFINE PROCEDURE {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE,
        )
        return ddl
    except Exception as e:
        return f"-- FAILED PROCEDURE {fq(name, schema)} : {e}"


# Map of object types to their custom definition handlers
CUSTOM_HANDLERS = {
    "STAGE": stage_define,
    "STREAM": stream_define,
    "SEQUENCE": sequence_define,
    "FILE FORMAT": file_format_define,
}


def generate_definition(obj_type, name, schema, signature=None, ddl_type=None):
    """Route to the correct definition generator."""
    if obj_type == "PROCEDURE":
        return procedure_define(name, schema, signature or "()")
    if obj_type in CUSTOM_HANDLERS:
        return CUSTOM_HANDLERS[obj_type](name, schema)
    return generic_ddl_define(obj_type, name, schema, ddl_type)


# ============================================================
# OBJECT DISCOVERY
# ============================================================

def discover_objects(schema):
    """Discover all objects in a schema using the registry."""
    fqn = f"{DATABASE}.{schema}"
    objects = []
    dynamic_table_names = set()

    for obj_type, _folder, show_cmd, _uses_ddl, _ddl_override in OBJECT_REGISTRY:

        # Procedures use INFORMATION_SCHEMA instead of SHOW
        if obj_type == "PROCEDURE":
            try:
                proc_rows = session.sql(f"""
                    SELECT *
                    FROM {DATABASE}.INFORMATION_SCHEMA.PROCEDURES
                    WHERE PROCEDURE_SCHEMA = '{schema}'
                """).collect()

                for r in proc_rows:
                    row = {k.upper(): v for k, v in r.asDict().items()}
                    if is_system_procedure(row, DATABASE, schema):
                        continue
                    name = row["PROCEDURE_NAME"]
                    sig = row.get("ARGUMENT_SIGNATURE") or "()"
                    objects.append((name, obj_type, sig))
            except Exception as e:
                print(f"  SKIPPED PROCEDURES: {e}")
            continue

        if not show_cmd:
            continue

        try:
            rows = session.sql(show_cmd.format(fqn=fqn)).collect()
            for r in rows:
                name = r["name"]

                # Track dynamic tables to exclude from regular tables
                if obj_type == "DYNAMIC TABLE":
                    dynamic_table_names.add(name)
                elif obj_type == "TABLE" and name in dynamic_table_names:
                    continue

                objects.append((name, obj_type, None))
        except Exception as e:
            print(f"  SKIPPED {obj_type}: {e}")

    return objects


# ============================================================
# MAIN — LOOP OVER ALL SCHEMAS
# ============================================================

print(f"\nProcessing {len(SCHEMAS)} schema(s): {SCHEMAS}\n")

total_objects = 0

for _current_schema in SCHEMAS:
    print(f"\n{'='*60}")
    print(f"SCHEMA: {DATABASE}.{_current_schema}")
    print(f"{'='*60}\n")

    # Create ALL folder structures for this schema (even if empty)
    schema_root = TARGET_ROOT / _current_schema
    for folder in sorted(set(FOLDER_MAP.values())):
        folder_path = schema_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        gitkeep = folder_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("")

    print(f"Created folder structure: {schema_root}")

    # Discover objects
    objects = discover_objects(_current_schema)
    print(f"\nObjects found in {_current_schema}: {len(objects)}")
    total_objects += len(objects)

    # Generate definitions
    print(f"\n--- Generating definitions for {_current_schema} ---\n")

    for name, obj_type, signature in objects:
        try:
            # Find ddl_type override from registry
            ddl_type = None
            for reg_type, _, _, _, reg_override in OBJECT_REGISTRY:
                if reg_type == obj_type:
                    ddl_type = reg_override
                    break

            result = generate_definition(obj_type, name, _current_schema, signature, ddl_type)

            file_path = get_path(obj_type, name, _current_schema)
            file_path.write_text(result, encoding="utf-8")
            print(f"  WROTE: {file_path.relative_to(TARGET_ROOT)}")

        except Exception as e:
            print(f"  FAILED {obj_type} {name}: {e}")

print(f"\n{'='*60}")
print(f"TOTAL OBJECTS ACROSS ALL SCHEMAS: {total_objects}")
print("DONE")
