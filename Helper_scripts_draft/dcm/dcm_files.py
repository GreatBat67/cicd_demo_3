# Script to generate DCM definition files from Snowflake schema objects

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
    "PATIENTS","HOSPITALS",
    "UTILITIES"]  
TARGET_DB = "CICD_AUTOMATION{{env_suffix}}"

# Roles that indicate system-owned procedures 
SYSTEM_OWNERS = {"SYSTEM", "SNOWFLAKE", "ACCOUNTADMIN", "ORGADMIN"}

# ============================================================
# PATH
# ============================================================

from pathlib import Path

current = Path.cwd()

# Locate the dcm_automation project
workspace_root = None

for parent in [current] + list(current.parents):
    if (parent / "dcm_automation").exists():
        workspace_root = parent
        break

if workspace_root is None:
    raise RuntimeError("Could not locate dcm_automation project.")

TARGET_ROOT = (
    workspace_root
    / "dcm_automation"
    / "sources"
    / "definitions"
)

print(f"Writing definitions to: {TARGET_ROOT}")

# ============================================================
# OBJECT FOLDER MAP
# ============================================================

FOLDER_MAP = {
    "TABLE": "tables",
    "VIEW": "views",
    "DYNAMIC TABLE": "dynamic_tables",
    "MATERIALIZED VIEW": "materialized_views",
    "EXTERNAL TABLE": "external_tables",
    "STAGE": "stages",
    "STREAM": "streams",
    "TASK": "tasks",
    "FILE FORMAT": "file_formats",
    "PROCEDURE": "stored_procedures",
    "FUNCTION": "functions",
    "PIPE": "pipes",
    "SEQUENCE": "sequences",
    "MASKING POLICY": "masking_policies",
    "ROW ACCESS POLICY": "row_access_policies",
    "TAG": "tags",
    "ALERT": "alerts",
    "OTHER": "others"
}

# ============================================================
# HELPERS
# ============================================================

def fq(name, schema):
    return f"{TARGET_DB}.{schema}.{name}"


def replace_env(text):
    if not text:
        return text
    return re.sub(
        rf"\b{DATABASE}\b",
        TARGET_DB,
        text,
        flags=re.IGNORECASE
    )


def get_path(obj_type, object_name, schema):
    """Returns the destination SQL file path for the object, organized by schema."""
    folder = FOLDER_MAP.get(obj_type, "others")
    folder_path = TARGET_ROOT / schema / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path / f"{object_name}.sql"


def is_system_procedure(row, database, current_schema):
    """Exclude system or non-user owned stored procedures."""

    owner = (row.get("owner") or "").upper()
    name = (row.get("name") or "").upper()
    catalog = (row.get("catalog_name") or "").upper()
    schema_name = (row.get("schema_name") or "").upper()
    is_builtin = (row.get("is_builtin") or "").upper()

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

def ddl_define(obj_type, name, schema):
    ddl = session.sql(
        f"""
        SELECT GET_DDL(
            '{obj_type}',
            '{DATABASE}.{schema}.{name}'
        )
        """
    ).collect()[0][0]

    ddl = replace_env(ddl)

    ddl = re.sub(
        r"CREATE\s+(OR\s+REPLACE\s+)?",
        "",
        ddl,
        flags=re.IGNORECASE
    )

    ddl = re.sub(
        r"^(.*?)\(",
        f"DEFINE {obj_type} {fq(name, schema)}(",
        ddl,
        flags=re.IGNORECASE | re.DOTALL
    )

    return ddl


def stage_define(name, schema):
    try:
        rows = session.sql(
            f"SHOW STAGES IN SCHEMA {DATABASE}.{schema}"
        ).collect()

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


def file_format_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'FILE FORMAT',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?FILE\s+FORMAT\s+[^\s]+",
            f"DEFINE FILE FORMAT {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED FILE FORMAT {fq(name, schema)} : {e}"


def task_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'TASK',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?TASK\s+[^\s]+",
            f"DEFINE TASK {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED TASK {fq(name, schema)} : {e}"


def stream_define(name, schema):
    rows = session.sql(
        f"SHOW STREAMS IN SCHEMA {DATABASE}.{schema}"
    ).collect()

    for r in rows:
        if r["name"] == name:
            return f"""
DEFINE STREAM {fq(name, schema)}
AS
SELECT *
FROM {r.get('table_name','')}
"""

    return f"-- FAILED STREAM {fq(name, schema)}"


def procedure_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'PROCEDURE',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\s+[^\s(]+",
            f"DEFINE PROCEDURE {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED PROCEDURE {fq(name, schema)} : {e}"


def function_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'FUNCTION',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?FUNCTION\s+[^\s(]+",
            f"DEFINE FUNCTION {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED FUNCTION {fq(name, schema)} : {e}"


def pipe_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'PIPE',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?PIPE\s+[^\s]+",
            f"DEFINE PIPE {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED PIPE {fq(name, schema)} : {e}"


def sequence_define(name, schema):
    try:
        rows = session.sql(
            f"SHOW SEQUENCES IN SCHEMA {DATABASE}.{schema}"
        ).collect()

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


def masking_policy_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'MASKING_POLICY',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?MASKING\s+POLICY\s+[^\s(]+",
            f"DEFINE MASKING POLICY {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED MASKING POLICY {fq(name, schema)} : {e}"


def row_access_policy_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'ROW_ACCESS_POLICY',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?ROW\s+ACCESS\s+POLICY\s+[^\s(]+",
            f"DEFINE ROW ACCESS POLICY {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED ROW ACCESS POLICY {fq(name, schema)} : {e}"


def tag_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'TAG',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?TAG\s+[^\s(]+",
            f"DEFINE TAG {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED TAG {fq(name, schema)} : {e}"


def alert_define(name, schema):
    try:
        ddl = session.sql(
            f"""
            SELECT GET_DDL(
                'ALERT',
                '{DATABASE}.{schema}.{name}'
            )
            """
        ).collect()[0][0]

        ddl = replace_env(ddl)
        ddl = re.sub(
            r"CREATE\s+(OR\s+REPLACE\s+)?ALERT\s+[^\s]+",
            f"DEFINE ALERT {fq(name, schema)}",
            ddl,
            flags=re.IGNORECASE
        )

        return ddl

    except Exception as e:
        return f"-- FAILED ALERT {fq(name, schema)} : {e}"


# ============================================================
# MAIN — LOOP OVER ALL SCHEMAS
# ============================================================

print(f"\nProcessing {len(SCHEMAS)} schema(s): {SCHEMAS}\n")

total_objects = 0

for _current_schema in SCHEMAS:
    print(f"\n{'='*60}")
    print(f"SCHEMA: {DATABASE}.{_current_schema}")
    print(f"{'='*60}\n")

    # Create folder structure for this schema
    schema_root = TARGET_ROOT / _current_schema
    for folder in sorted(set(FOLDER_MAP.values())):
        folder_path = schema_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        gitkeep = folder_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("")

    print(f"Created folder structure: {schema_root}")

    # --------------------------------------------------------
    # COLLECT OBJECTS FOR THIS SCHEMA
    # --------------------------------------------------------
    objects = []

    # DYNAMIC TABLES
    dynamic_table_names = set()
    dynamic_tables =  session.sql(
        f"SHOW DYNAMIC TABLES IN SCHEMA {DATABASE}.{_current_schema}"
    ).collect()
    for r in dynamic_tables:
        objects.append((r["name"], "DYNAMIC TABLE"))
        dynamic_table_names.add(r["name"])

    # NORMAL TABLES ONLY
    tables = session.sql(
        f"SHOW TABLES IN SCHEMA {DATABASE}.{_current_schema}"
    ).collect()
    for r in tables:
        if r["name"] not in dynamic_table_names:
            objects.append((r["name"], "TABLE"))

    # VIEWS
    objects += [
        (r["name"], "VIEW")
        for r in session.sql(
            f"SHOW VIEWS IN SCHEMA {DATABASE}.{_current_schema}"
        ).collect()
    ]

    # STAGES
    objects += [
        (r["name"], "STAGE")
        for r in session.sql(
            f"SHOW STAGES IN SCHEMA {DATABASE}.{_current_schema}"
        ).collect()
    ]

    # FILE FORMATS
    objects += [
        (r["name"], "FILE FORMAT")
        for r in session.sql(
            f"SHOW FILE FORMATS IN SCHEMA {DATABASE}.{_current_schema}"
        ).collect()
    ]

    # STREAMS
    objects += [
        (r["name"], "STREAM")
        for r in session.sql(
            f"SHOW STREAMS IN SCHEMA {DATABASE}.{_current_schema}"
        ).collect()
    ]

    # TASKS
    objects += [
        (r["name"], "TASK")
        for r in session.sql(
            f"SHOW TASKS IN SCHEMA {DATABASE}.{_current_schema}"
        ).collect()
    ]

    # PROCEDURES — filter out system-owned procs
    try:
        proc_rows = session.sql(f"""
            SELECT *
            FROM {DATABASE}.INFORMATION_SCHEMA.PROCEDURES
            WHERE PROCEDURE_SCHEMA = '{_current_schema}'
        """).collect()

        for r in proc_rows:
            row = {k.upper(): v for k, v in r.asDict().items()}

            if is_system_procedure(row, DATABASE, _current_schema):
                print(f"  SKIPPED system proc: {row.get('PROCEDURE_NAME')}")
                continue

            name = row["PROCEDURE_NAME"]
            signature = row.get("ARGUMENT_SIGNATURE") or "()"
            objects.append((name, "PROCEDURE", signature))

    except Exception as e:
        print(f"SKIPPED PROCEDURES: {e}")

    # FUNCTIONS
    try:
        objects += [
            (r["name"], "FUNCTION")
            for r in session.sql(
                f"SHOW USER FUNCTIONS IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED FUNCTIONS: {e}")

    # PIPES
    try:
        objects += [
            (r["name"], "PIPE")
            for r in session.sql(
                f"SHOW PIPES IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED PIPES: {e}")

    # SEQUENCES
    try:
        objects += [
            (r["name"], "SEQUENCE")
            for r in session.sql(
                f"SHOW SEQUENCES IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED SEQUENCES: {e}")

    # MASKING POLICIES
    try:
        objects += [
            (r["name"], "MASKING POLICY")
            for r in session.sql(
                f"SHOW MASKING POLICIES IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED MASKING POLICIES: {e}")

    # ROW ACCESS POLICIES
    try:
        objects += [
            (r["name"], "ROW ACCESS POLICY")
            for r in session.sql(
                f"SHOW ROW ACCESS POLICIES IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED ROW ACCESS POLICIES: {e}")

    # TAGS
    try:
        objects += [
            (r["name"], "TAG")
            for r in session.sql(
                f"SHOW TAGS IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED TAGS: {e}")

    # ALERTS
    try:
        objects += [
            (r["name"], "ALERT")
            for r in session.sql(
                f"SHOW ALERTS IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED ALERTS: {e}")

    # EXTERNAL TABLES
    try:
        objects += [
            (r["name"], "EXTERNAL TABLE")
            for r in session.sql(
                f"SHOW EXTERNAL TABLES IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED EXTERNAL TABLES: {e}")

    # MATERIALIZED VIEWS
    try:
        objects += [
            (r["name"], "MATERIALIZED VIEW")
            for r in session.sql(
                f"SHOW MATERIALIZED VIEWS IN SCHEMA {DATABASE}.{_current_schema}"
            ).collect()
        ]
    except Exception as e:
        print(f"SKIPPED MATERIALIZED VIEWS: {e}")

    print(f"\nObjects found in {_current_schema}: {len(objects)}")
    total_objects += len(objects)

    # --------------------------------------------------------
    # GENERATE DEFINITIONS FOR THIS SCHEMA
    # --------------------------------------------------------

    print(f"\n--- Generating definitions for {_current_schema} ---\n")

    for item in objects:
        if len(item) == 3:
            name, obj_type, signature = item
        else:
            name, obj_type = item
            signature = None

        try:
            if obj_type in [
                "TABLE", "VIEW", "DYNAMIC TABLE",
                "MATERIALIZED VIEW", "EXTERNAL TABLE"
            ]:
                result = ddl_define(obj_type, name, _current_schema)
            elif obj_type == "STAGE":
                result = stage_define(name, _current_schema)
            elif obj_type == "FILE FORMAT":
                result = file_format_define(name, _current_schema)
            elif obj_type == "TASK":
                result = task_define(name, _current_schema)
            elif obj_type == "STREAM":
                result = stream_define(name, _current_schema)
            elif obj_type == "PROCEDURE":
                result = session.sql(f"""
                    SELECT GET_DDL(
                        'PROCEDURE',
                        '{DATABASE}.{_current_schema}.{name}{signature}'
                    )
                """).collect()[0][0]

                result = replace_env(result)

                result = re.sub(
                    r"CREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\s+[^\s(]+",
                    f"DEFINE PROCEDURE {fq(name, _current_schema)}",
                    result,
                    flags=re.IGNORECASE
                )
            elif obj_type == "FUNCTION":
                result = function_define(name, _current_schema)
            elif obj_type == "PIPE":
                result = pipe_define(name, _current_schema)
            elif obj_type == "SEQUENCE":
                result = sequence_define(name, _current_schema)
            elif obj_type == "MASKING POLICY":
                result = masking_policy_define(name, _current_schema)
            elif obj_type == "ROW ACCESS POLICY":
                result = row_access_policy_define(name, _current_schema)
            elif obj_type == "TAG":
                result = tag_define(name, _current_schema)
            elif obj_type == "ALERT":
                result = alert_define(name, _current_schema)
            else:
                result = f"-- UNSUPPORTED {obj_type} {fq(name, _current_schema)}"

            file_path = get_path(obj_type, name, _current_schema)
            file_path.write_text(result, encoding="utf-8")
            print(f"WROTE: {file_path}")

        except Exception as e:
            print(f"FAILED {obj_type} {name}: {e}")

print(f"\n{'='*60}")
print(f"TOTAL OBJECTS ACROSS ALL SCHEMAS: {total_objects}")
print("DONE")
