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

# Variables
LOGS_DIR = cfg.LOGS_DIR
DATABASES = cfg.DATABASES
SCHEMAS = cfg.SCHEMAS
ROLES = cfg.ROLES
DBT = cfg.DBT
DBT_TARGETS = cfg.DBT_TARGETS
DBT_SCHEMAS = cfg.DBT_SCHEMAS
# ============================================================
# OUTPUT LOCATION
# ============================================================

OUTPUT_FILE = LOGS_DIR / "generate_databases.sql"

# ============================================================
# CONFIG
# ============================================================

PROJECT = config.project
DATABASES = config.databases
SCHEMAS = config.schemas
ROLES = config.roles

ADMIN_ROLE = config.snowflake["admin_role"]

SCHEMA_CREATE_GRANTS = [
    "CREATE TABLE",
    "CREATE VIEW",
    "CREATE DYNAMIC TABLE",
    "CREATE STAGE",
    "CREATE STREAM",
    "CREATE TASK",
    "CREATE FILE FORMAT",
    "CREATE PROCEDURE",
    "CREATE FUNCTION",
    "CREATE DCM PROJECT",
]
# ============================================================
# GENERATE SQL
# ============================================================

sql = []

# ------------------------------------------------------------
# ADMIN ROLE
# ------------------------------------------------------------

sql.append(f"USE ROLE {ADMIN_ROLE};")
sql.append("")

# ------------------------------------------------------------
# CREATE DATABASES & SCHEMAS
# ------------------------------------------------------------

sql.append("-- ====================================================")
sql.append("-- CREATE DATABASES & SCHEMAS")
sql.append("-- ====================================================")
sql.append("")

for db in DATABASES:

    db_name = db["name"]

    sql.append(f"CREATE DATABASE IF NOT EXISTS {db_name};")

    # Merge application schemas and DBT schemas
    ALL_SCHEMAS = list(SCHEMAS)

    for schema in DBT_SCHEMAS:
        if schema not in ALL_SCHEMAS:
            ALL_SCHEMAS.append(schema)

    # Create all schemas
    for schema in ALL_SCHEMAS:
        sql.append(
            f"CREATE SCHEMA IF NOT EXISTS {db_name}.{schema};"
        )

    sql.append("")

# ------------------------------------------------------------
# CREATE ROLES
# ------------------------------------------------------------

sql.append("-- ====================================================")
sql.append("-- CREATE ROLES")
sql.append("-- ====================================================")
sql.append("")

for role in ROLES.keys():
    sql.append(f"CREATE ROLE IF NOT EXISTS {role};")

    # Don't grant a role to itself
    if role.strip().upper() != ADMIN_ROLE.strip().upper():
        sql.append(f"GRANT ROLE {role} TO ROLE {ADMIN_ROLE};")

sql.append("")

# ------------------------------------------------------------
# ROLE GRANTS
# ------------------------------------------------------------

for role, policy in ROLES.items():

    sql.append("-- ====================================================")
    sql.append(f"-- ROLE : {role}")
    sql.append("-- ====================================================")
    sql.append("")

    for db in DATABASES:

        db_name = db["name"]

        # Merge application schemas and DBT schemas
        ALL_SCHEMAS = list(SCHEMAS)

        for schema in DBT_SCHEMAS:
            if schema not in ALL_SCHEMAS:
                ALL_SCHEMAS.append(schema)

        sql.append(f"-- Database : {db_name}")
        sql.append(f"GRANT USAGE ON DATABASE {db_name} TO ROLE {role};")

        if policy.get("create", False):
            sql.append(
                f"GRANT CREATE SCHEMA ON DATABASE {db_name} TO ROLE {role};"
            )

        sql.append("")

        # ----------------------------------------------------
        # Schema Grants
        # ----------------------------------------------------

        for schema in ALL_SCHEMAS:

            full_schema = f"{db_name}.{schema}"

            sql.append("-- ----------------------------------------------------")
            sql.append(f"-- Schema : {schema}")
            sql.append("-- ----------------------------------------------------")

            # Usage
            sql.append(
                f"GRANT USAGE ON SCHEMA {full_schema} TO ROLE {role};"
            )

            # Create privileges
            if policy.get("create", False):
                sql.append(
                    f"GRANT {', '.join(SCHEMA_CREATE_GRANTS)} "
                    f"ON SCHEMA {full_schema} TO ROLE {role};"
                )

            # Read privileges
            if policy.get("read", False):
                sql.append(
                    f"GRANT SELECT ON ALL TABLES IN SCHEMA {full_schema} TO ROLE {role};"
                )
                sql.append(
                    f"GRANT SELECT ON FUTURE TABLES IN SCHEMA {full_schema} TO ROLE {role};"
                )
                sql.append(
                    f"GRANT SELECT ON ALL VIEWS IN SCHEMA {full_schema} TO ROLE {role};"
                )
                sql.append(
                    f"GRANT SELECT ON FUTURE VIEWS IN SCHEMA {full_schema} TO ROLE {role};"
                )

            sql.append("")

        sql.append("")

    # --------------------------------------------------------
    # ACCOUNT LEVEL GRANTS
    # --------------------------------------------------------

    sql.append(f"GRANT EXECUTE TASK ON ACCOUNT TO ROLE {role};")
    sql.append(f"GRANT CREATE ROLE ON ACCOUNT TO ROLE {role};")
    sql.append(f"GRANT MANAGE GRANTS ON ACCOUNT TO ROLE {role};")
    
    sql.append("")
    
# ============================================================
# WRITE FILE
# ============================================================

OUTPUT_FILE.write_text("\n".join(sql), encoding="utf-8")

print(f"\nSQL written successfully:\n{OUTPUT_FILE.resolve()}")