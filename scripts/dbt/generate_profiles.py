from pathlib import Path
import sys
import importlib

sys.dont_write_bytecode = True

# ============================================================
# LOAD CONFIG
# ============================================================

ROOT = Path.cwd().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config.config as cfg

importlib.reload(cfg)

config = cfg.config

# ============================================================
# CONFIG
# ============================================================

DATABASES = cfg.DATABASES

DBT_PROFILE_NAME = cfg.DBT_PROFILE_NAME
DBT_DEFAULT_TARGET = cfg.DBT_DEFAULT_TARGET
DBT_TARGETS = cfg.DBT_TARGETS

DBT_PROJECT_DIR = cfg.DBT_PROJECT_DIR
SNOWFLAKE = cfg.SNOWFLAKE

PROFILES_FILE = DBT_PROJECT_DIR / "profiles.yml"

# ============================================================
# GENERATE PROFILES.YML
# ============================================================

def main():

    if not DATABASES:
        print("No databases defined in project_config.yml")
        return

    if not DBT_TARGETS:
        print("No DBT targets defined in project_config.yml")
        return

    dbt = config.dbt
    snowflake = config.snowflake

    profile_name = dbt["profile_name"]
    default_target = dbt["default_target"]
    target_prefix = dbt["target_prefix"]
    targets = dbt["targets"]

    lines = [
        f"{profile_name}:",
        f"  target: {default_target}",
        "",
        "  outputs:",
        "",
    ]

    for db in DATABASES:

        environment = db["environment"]

        target = targets.get(environment)

        if target is None:
            continue

        target_name = f"{target_prefix}_{environment}"

        lines.extend([
            f"    {target_name}:",
            "      type: snowflake",
            f"      account: {snowflake['account_identifier']}",
            f"      user: {snowflake['user']}",
            f"      role: {target['role']}",
            f"      database: {db['name']}",
            f"      warehouse: {snowflake['warehouse']}",
            f"      schema: {target['schema']}",
            f"      threads: {snowflake.get('threads', 4)}",
            f"      client_session_keep_alive: {str(snowflake.get('client_session_keep_alive', False)).lower()}",
            "",
        ])

    DBT_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    PROFILES_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 60)
    print("profiles.yml generated successfully.")
    print("=" * 60)
    print(f"DBT Project    : {DBT_PROJECT_DIR}")
    print(f"Profiles File  : {PROFILES_FILE}")
    print(f"Profile Name   : {DBT_PROFILE_NAME}")
    print(f"Default Target : {DBT_DEFAULT_TARGET}")

    print("\nConfigured Targets")
    print("-" * 60)

    for db in DATABASES:

        environment = db["environment"]

        target = DBT_TARGETS.get(environment)

        if target is None:
            continue

        print(
            f"{environment:<6}"
            f" Database={db['name']:<25}"
            f" Role={target['role']:<30}"
            f" Schema={target['schema']}"
        )

    print("=" * 60)
    print("Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()