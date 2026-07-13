from pathlib import Path
import sys
import yaml
sys.dont_write_bytecode = True

# import importlib
# import config.config
# importlib.reload(config.config)


# ============================================================
# LOAD CONFIGURATION
# ============================================================

ROOT = Path.cwd().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.config import (
    config,
    PROJECT_DIR,
    MANIFEST_FILE,
)

# ============================================================
# YAML
# ============================================================

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


# ============================================================
# CONFIG
# ============================================================

PROJECT = config.project
PROJECT_NAME = PROJECT["name"]

SNOWFLAKE = config.snowflake

DATABASES = config.databases
SCHEMAS = config.schemas
ROLES = config.roles
DCM_PROJECT = config.dcm_project

MANIFEST_VERSION = 2
PROJECT_TYPE = "DCM_PROJECT"

ACCOUNT_IDENTIFIER = SNOWFLAKE["account_identifier"]
WAREHOUSE = SNOWFLAKE["warehouse"]
WH_SIZE = SNOWFLAKE["warehouse_size"]

DCM_SCHEMA = config.dcm_project["schema"]
PROJECT_OWNER = config.dcm_project["owner_role"]

DEFAULT_TARGET = f"DCM_{DATABASES[0]['environment']}"

# ============================================================
# BUILD MANIFEST
# ============================================================

def build_manifest():

    targets = {}
    configurations = {}

    for db in DATABASES:

        environment = db["environment"]
        database = db["name"]

        target_name = f"DCM_{environment}"

        project_name = (
            f"{database}.{DCM_SCHEMA}.{PROJECT_NAME.lower()}"
        )

        targets[target_name] = {
            "account_identifier": ACCOUNT_IDENTIFIER,
            "project_name": project_name,
            "project_owner": PROJECT_OWNER,
            "templating_config": environment,
        }

        configurations[environment] = {
            "environment": environment,
            "env_suffix": f"_{environment}",
            "database": database,
            "schemas": SCHEMAS,
            "dcm_schema": DCM_SCHEMA,
            "project_name": project_name,
            "project_owner": PROJECT_OWNER,
            "roles": list(ROLES.keys()),
        }

    return {
        "manifest_version": MANIFEST_VERSION,
        "type": PROJECT_TYPE,
        "default_target": DEFAULT_TARGET,
        "targets": targets,
        "templating": {
            "defaults": {
                "project_owner_role": PROJECT_OWNER,
                "warehouse": WAREHOUSE,
                "wh_size": WH_SIZE,
                "dcm_schema": DCM_SCHEMA,
            },
            "configurations": configurations,
        },
    }


# ============================================================
# WRITE MANIFEST
# ============================================================

def write_manifest(manifest):

    with MANIFEST_FILE.open("w", encoding="utf-8") as f:
        yaml.dump(
            manifest,
            f,
            Dumper=NoAliasDumper,
            default_flow_style=False,
            sort_keys=False,
        )

    return MANIFEST_FILE

# ============================================================
# MAIN
# ============================================================

def main():

    manifest = build_manifest()

    manifest_path = write_manifest(manifest)

    print("=" * 60)
    print("Manifest generated successfully.")
    print(f"Output : {manifest_path}")
    print("=" * 60)

    # print(
    #     yaml.dump(
    #         manifest,
    #         Dumper=NoAliasDumper,
    #         default_flow_style=False,
    #         sort_keys=False,
    #     )
    # )


if __name__ == "__main__":
    main()