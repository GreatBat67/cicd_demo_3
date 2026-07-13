import sys
from pathlib import Path
import importlib.util

sys.dont_write_bytecode = True


# ============================================================
# CONFIG
# ============================================================

DATABASES = [
    "CICD_AUTOMATION_DEV",
    "CICD_AUTOMATION_QA",
    "CICD_AUTOMATION_PROD",
]

SCHEMAS = [
    "PATIENTS",
    "HOSPITALS",
    "UTILITIES",
]

ROLES = [
    "GITHUB_CICD_DEMO_ROLE",
    # "DEVELOPER_ROLE",
    # "ANALYST_ROLE",
]

ADMIN_ROLE = "PSEUDO_ACCOUNTADMIN"

# ============================================================
# ROLE PERMISSIONS (EXTENSIBLE)
# ============================================================

ROLE_POLICY = {
    "GITHUB_CICD_DEMO_ROLE": {
        "create": True,
        "read": True,
        "ownership": True,
    },

    # Future roles :
    # "DEVELOPER_ROLE": {
    #     "create": True,
    #     "read": True,
    #     "ownership": False,
    # },

    # "ANALYST_ROLE": {
    #     "create": False,
    #     "read": True,
    #     "ownership": False,
    # },
}

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
    "CREATE DCM PROJECT"
]


# ============================================================
# OUTPUT LOCATION
# ============================================================

CURRENT_DIR = Path.cwd()
BASE_DIR = CURRENT_DIR.parent

TARGET_ROOT = BASE_DIR / "logs"
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = TARGET_ROOT / "create_databases_and_grants.sql"

print("OUTPUT DIRECTORY:", TARGET_ROOT)
print("OUTPUT FILE:", OUTPUT_FILE)

# ============================================================
# GENERATE SQL
# ============================================================

sql = []

# ------------------------------------------------------------
# CREATE DATABASE + SCHEMAS
# ------------------------------------------------------------
sql.append(f"USE ROLE {ADMIN_ROLE};")
sql.append("")

for db in DATABASES:
    sql.append(f"CREATE DATABASE IF NOT EXISTS {db};")

    for schema in SCHEMAS:
        sql.append(f"CREATE SCHEMA IF NOT EXISTS {db}.{schema};")

    sql.append("")

# ------------------------------------------------------------
# CREATE ROLES
# ------------------------------------------------------------

sql.append("-- ====================================================")
sql.append("-- ROLE CREATION")
sql.append("-- ====================================================")
sql.append("")

# Switch to the admin role
sql.append(f"USE ROLE {ADMIN_ROLE};")
sql.append("")

# Create roles if they don't already exist
for role in ROLES:
    sql.append(f"CREATE ROLE IF NOT EXISTS {role};")
    sql.append(f"GRANT ROLE {role} TO ROLE {ADMIN_ROLE};")

sql.append("")

# ------------------------------------------------------------
# USE ADMIN ROLE FOR OWNERSHIP TRANSFER
# ------------------------------------------------------------

sql.append(f"USE ROLE {ADMIN_ROLE};")
sql.append("")

# ------------------------------------------------------------
# GRANTS FOR EACH ROLE
# ------------------------------------------------------------

for role in ROLES:

    policy = ROLE_POLICY.get(role, {
        "create": False,
        "read": False,
        "ownership": False
    })

    sql.append(f"-- ====================================================")
    sql.append(f"-- GRANTS FOR ROLE: {role}")
    sql.append(f"-- ====================================================")
    sql.append("")

    for db in DATABASES:

        # DATABASE LEVEL
        sql.append(f"-- Database: {db}")

        sql.append(f"GRANT USAGE ON DATABASE {db} TO ROLE {role};")

        if policy["create"]:
            sql.append(
                f"GRANT CREATE SCHEMA ON DATABASE {db} TO ROLE {role};"
            )

        sql.append("")

        for schema in SCHEMAS:

            full_schema = f"{db}.{schema}"

            # SCHEMA USAGE
            sql.append(f"GRANT USAGE ON SCHEMA {full_schema} TO ROLE {role};")

            # CREATE PRIVILEGES
            if policy["create"]:
                sql.append(
                    f"GRANT {', '.join(SCHEMA_CREATE_GRANTS)} "
                    f"ON SCHEMA {full_schema} TO ROLE {role};"
                )

            # READ PRIVILEGES
            if policy["read"]:
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
                sql.append(
                    f"GRANT EXECUTE TASK ON ACCOUNT  TO ROLE {role};"
                )
                sql.append(
                     f"GRANT CREATE ROLE ON ACCOUNT TO ROLE {role};" 
                )

            sql.append("")

        sql.append("")

# ------------------------------------------------------------
# 1. CREATE ROLES + ROLE HIERARCHY
# ------------------------------------------------------------

sql.append("-- ====================================================")
sql.append("-- ROLE CREATION")
sql.append("-- ====================================================")
sql.append("")

for role in ROLES:
#     sql.append(f"CREATE ROLE IF NOT EXISTS {role};")

# sql.append("")

# ------------------------------------------------------------
# 2. GRANT ROLE CREATION PRIVILEGE TO GITHUB ROLE
# ------------------------------------------------------------

    sql.append("-- Allow GitHub role to create new roles")
    sql.append(
        "GRANT CREATE ROLE ON ACCOUNT TO ROLE GITHUB_CICD_DEMO_ROLE;"
    )
    sql.append("")

# ============================================================
# WRITE FILE
# ============================================================

OUTPUT_FILE.write_text("\n".join(sql), encoding="utf-8")

print(f"\nSQL written successfully to:\n{OUTPUT_FILE.resolve()}")