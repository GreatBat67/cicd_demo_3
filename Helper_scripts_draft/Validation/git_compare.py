# Compare Git repo objects against Snowflake and store results in a table

from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.types import StructType, StructField, StringType, TimestampType
from datetime import datetime

session = get_active_session()

# ============================================================
# PARAMETERS 
# ============================================================
REPO_PATH = "@DISHA_DCM.INTEGRATION.DCM_PROJECT_REPO/branches/dev_dcm_disha/Projects/DDL"
TARGET_DBS = "CICD_AUTOMATION_DEV"
SCHEMAS = "PATIENTS,HOSPITALS,UTILITIES"
RESULTS_TABLE = "CICD_AUTOMATION_DEV.VALIDATION.GIT_SF_COMPARE_RESULTS"
# ============================================================

RESULT_SCHEMA = StructType([
    StructField("FILE_PATH", StringType()),
    StructField("OBJECT_TYPE", StringType()),
    StructField("FULL_NAME", StringType()),
    StructField("STATUS", StringType()),
    StructField("RUN_DATETIME", TimestampType()),
])

# Maps folder names to SHOW command object types — dynamically covers all DDL subfolders
FOLDER_MAP = {
    "tables": "TABLES",
    "views": "VIEWS",
    "tasks": "TASKS",
    "stages": "STAGES",
    "file_formats": "FILE FORMATS",
    "procedures": "PROCEDURES",
    "functions": "FUNCTIONS",
    "dynamic_tables": "DYNAMIC TABLES",
    "streams": "STREAMS",
    "sequences": "SEQUENCES",
    "pipes": "PIPES",
    "alerts": "ALERTS",
    "masking_policies": "MASKING POLICIES",
    "row_access_policies": "ROW ACCESS POLICIES",
    "tags": "TAGS",
    "network_rules": "NETWORK RULES",
    "secrets": "SECRETS",
    "external_tables": "EXTERNAL TABLES",
}


def get_git_objects(repo_path):
    """Parse Git repo stage listing. Structure: .../DDL/<SCHEMA>/<folder>/<NAME>.sql"""
    rows = session.sql(f"LS {repo_path}").collect()
    git = {}

    for r in rows:
        p = r["name"]

        if not p.endswith(".sql"):
            continue

        parts = p.split("/")

        if "DDL" not in parts:
            continue

        try:
            idx = parts.index("DDL")
            schema = parts[idx + 1].upper()
            folder = parts[idx + 2].lower()
            name = parts[-1].replace(".sql", "").upper()

            show_keyword = FOLDER_MAP.get(folder)
            if not show_keyword:
                show_keyword = folder.replace("_", " ").upper()
                if not show_keyword.endswith("S"):
                    show_keyword += "S"

            key = (schema, name, show_keyword)
            git[key] = p
        except (IndexError, ValueError):
            continue

    return git


def compare(repo_path, target_dbs, schemas):
    """Compare Git objects against Snowflake across multiple databases."""
    db_list = [d.strip().upper() for d in target_dbs.split(",") if d.strip()]
    schema_list = [s.strip().upper() for s in schemas.split(",") if s.strip()] if schemas else []

    git_map = get_git_objects(repo_path)
    results = []
    run_time = datetime.now()

    show_cache = {}

    for (git_schema, name, show_keyword), path in git_map.items():
        if schema_list and git_schema not in schema_list:
            continue

        for db in db_list:
            cache_key = (db, git_schema, show_keyword)

            if cache_key not in show_cache:
                try:
                    sf = session.sql(
                        f"SHOW {show_keyword} IN SCHEMA {db}.{git_schema}"
                    ).collect()
                    show_cache[cache_key] = [r["name"].upper() for r in sf]
                except Exception:
                    show_cache[cache_key] = None

            sf_names = show_cache[cache_key]
            if sf_names is None:
                status = "SCHEMA_NOT_FOUND"
            elif name in sf_names:
                status = "IN_SYNC"
            else:
                status = "MISSING_IN_SNOWFLAKE"

            obj_type = show_keyword.rstrip("S") if show_keyword.endswith("S") and not show_keyword.endswith("SS") else show_keyword

            results.append((
                path,
                obj_type,
                f"{db}.{git_schema}.{name}",
                status,
                run_time,
            ))

    if not results:
        print("No objects found. Check REPO_PATH and folder structure.")
        results.append(("N/A", "N/A", "N/A", "NO_RESULTS", run_time))

    return session.create_dataframe(results, schema=RESULT_SCHEMA)


# --- Create table if not exists ---
session.sql(f"""
    CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
        FILE_PATH       STRING,
        OBJECT_TYPE     STRING,
        FULL_NAME       STRING,
        STATUS          STRING,
        RUN_DATETIME    TIMESTAMP_NTZ
    )
""").collect()

# --- Truncate and write fresh results ---
session.sql(f"TRUNCATE TABLE {RESULTS_TABLE}").collect()

df = compare(REPO_PATH, TARGET_DBS, SCHEMAS)
df.write.mode("append").save_as_table(RESULTS_TABLE)

print(f"Results written to {RESULTS_TABLE}")
df.show(100)
