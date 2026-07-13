from pathlib import Path
import sys
sys.dont_write_bytecode = True

ROOT = Path.cwd().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import config.config as cfg

importlib.reload(cfg)

config = cfg.config
LOGS_DIR = cfg.LOGS_DIR
PROJECT_DIR = cfg.PROJECT_DIR
# ============================================================
# OUTPUT LOCATION
# ============================================================

OUTPUT_FILE = LOGS_DIR / "create_dbt_project.sql"

# ============================================================
# CONFIG
# ============================================================

PROJECT_NAME = config.project["name"]

DATABASES = config.databases
SNOWFLAKE = config.snowflake
DBT = config.dbt

ADMIN_ROLE = SNOWFLAKE["admin_role"]

DBT_PROJECT = DBT["project"]
DBT_PROJECT_NAME = DBT_PROJECT["name"]
DBT_PROJECT_SCHEMA = DBT_PROJECT["schema"]
DBT_PROJECT_OWNER_ROLE = DBT_PROJECT["owner_role"]

DBT_TARGETS = DBT["targets"]

SNOWFLAKE_USER = SNOWFLAKE["user"]

DBT_PROJECT = DBT["project"]
DBT_PROJECT_NAME = DBT_PROJECT["name"]
DBT_PROJECT_SCHEMA = DBT_PROJECT["schema"]
DBT_PROJECT_OWNER_ROLE = DBT_PROJECT["owner_role"]
# DBT_VERSION = DBT_PROJECT["version"]

DBT_TARGET_PREFIX = DBT["target_prefix"]




# ============================================================
# GENERATE SQL
# ============================================================

sql = []

sql.extend(
    [
        "-- ====================================================",
        "-- CREATE DBT PROJECTS",
        "-- ====================================================",
        "",
    ]
)

for db in DATABASES:

    environment = db["environment"]
    database = db["name"]

    target = DBT_TARGETS.get(environment)

    if target is None:
        print(f"Skipping {environment}: No DBT target configured.")
        continue

    role = target["role"]

    sql.extend(
    [
        "-- ----------------------------------------------------",
        f"-- Environment : {environment}",
        "-- ----------------------------------------------------",
        f"USE ROLE {ADMIN_ROLE};",
        f"USE DATABASE {database};",
        f"USE SCHEMA {database}.{DBT_PROJECT_SCHEMA};",
        "",
        (
            f"CREATE DBT PROJECT IF NOT EXISTS "
            f"{database}.{DBT_PROJECT_SCHEMA}.{DBT_PROJECT_NAME}"
        ),
        (
            f"FROM 'snow://workspace/USER${SNOWFLAKE_USER}.PUBLIC."
            f"CI_CD_STANDARD_TIER_OFFERING_TEMPLATE/versions/live/"
            f"{DBT_PROJECT_NAME}/'"
        ),
        # f"DBT_VERSION = '{DBT_VERSION}'",
        f"DEFAULT_TARGET = '{DBT_TARGET_PREFIX}_{environment}'",
        "EXTERNAL_ACCESS_INTEGRATIONS = ()",
        f"COMMENT = 'DBT Project - {environment}';",
        "",
    ]
)


# ============================================================
# WRITE FILE
# ============================================================

OUTPUT_FILE.write_text(
    "\n".join(sql),
    encoding="utf-8",
)

print("=" * 60)
print("DBT Project SQL generated successfully.")
print(f"Output : {OUTPUT_FILE.resolve()}")
print("=" * 60)