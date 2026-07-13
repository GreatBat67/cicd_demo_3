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


from config.config import config,LOGS_DIR


# ============================================================
# CONFIG
# ============================================================

PROJECT_NAME = config.project["name"]

DATABASES = config.databases
DCM_PROJECT = config.dcm_project
SNOWFLAKE = config.snowflake

ADMIN_ROLE = SNOWFLAKE.get("admin_role")
DCM_SCHEMA = DCM_PROJECT["schema"]


# ============================================================
# OUTPUT LOCATION
# ============================================================


OUTPUT_FILE = LOGS_DIR / "create_dcm_projects.sql"


# ============================================================
# GENERATE SQL
# ============================================================

sql = []

sql.append("-- ====================================================")
sql.append("-- CREATE DCM PROJECTS")
sql.append("-- ====================================================")
sql.append("")

for db in DATABASES:

    db_name = db["name"]
    env = db.get("environment", db_name)

    sql.append("-- ----------------------------------------------------")
    sql.append(f"-- Environment : {env}")
    sql.append("-- ----------------------------------------------------")

    sql.append(f"USE ROLE {ADMIN_ROLE};")
    sql.append(f"USE DATABASE {db_name};")
    sql.append(f"USE SCHEMA {db_name}.{DCM_SCHEMA};")
    sql.append("")

    sql.append(
        f"CREATE DCM PROJECT IF NOT EXISTS "
        f"{db_name}.{DCM_SCHEMA}.{PROJECT_NAME}"
    )
    sql.append(f"COMMENT = 'DCM Project - {env}';")
    sql.append("")


# ============================================================
# WRITE FILE
# ============================================================

OUTPUT_FILE.write_text("\n".join(sql), encoding="utf-8")

print("=" * 60)
print("DCM Project SQL generated successfully.")
print(f"Output: {OUTPUT_FILE.resolve()}")
print("=" * 60)