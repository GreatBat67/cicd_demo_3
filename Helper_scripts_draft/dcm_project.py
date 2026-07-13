from pathlib import Path

# ============================================================
# CONSTANTS
# ============================================================

PROJECT_NAME = "DCM_AUTOMATION"
DCM_SCHEMA = "UTILITIES"

# ============================================================
# OUTPUT LOCATION
# ============================================================

CURRENT_DIR = Path.cwd()
BASE_DIR = CURRENT_DIR.parent

TARGET_ROOT = BASE_DIR / "logs"
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = TARGET_ROOT / "create_dcm_project.sql"

print("OUTPUT DIRECTORY:", TARGET_ROOT)
print("OUTPUT FILE:", OUTPUT_FILE)
# ============================================================
# ENVIRONMENTS
# ============================================================

ENVIRONMENTS = [
    {
        "env": "DEV",
        "database": "CICD_AUTOMATION_DEV",
        "schema": "UTILITIES",
        "role": "GITHUB_CICD_DEMO_ROLE"
    },
    {
        "env": "QA",
        "database": "CICD_AUTOMATION_QA",
        "schema": "UTILITIES",
        "role": "GITHUB_CICD_DEMO_ROLE"
    },
    {
        "env": "PROD",
        "database": "CICD_AUTOMATION_PROD",
        "schema": "UTILITIES",
        "role": "GITHUB_CICD_DEMO_ROLE"
    }
]

# ============================================================
# GENERATE SQL
# ============================================================

def generate_sql():
    sql_blocks = []

    for env in ENVIRONMENTS:
        sql_blocks.append(f"""
-- ============================================================
-- {env['env']}
-- ============================================================

USE ROLE {env['role']};
USE DATABASE {env['database']};
USE SCHEMA {env['database']}.{env['schema']};

CREATE DCM PROJECT IF NOT EXISTS {env['database']}.{env['schema']}.{PROJECT_NAME}
COMMENT = 'DCM Project - {env["env"]}';
""".strip())

    return "\n\n".join(sql_blocks)

# ============================================================
# WRITE FILE
# ============================================================

def write_file(sql):
    OUTPUT_FILE.write_text(sql, encoding="utf-8")
    print(f"\n SQL generated successfully: {OUTPUT_FILE}")

# ============================================================
# MAIN
# ============================================================

def main():
    sql = generate_sql()
    write_file(sql)

if __name__ == "__main__":
    main()