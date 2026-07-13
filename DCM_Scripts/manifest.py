
import yaml
from pathlib import Path


# ============================================================
# Disable YAML anchors/aliases
# ============================================================

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


# ============================================================
# CONFIGURATION
# ============================================================

MANIFEST_VERSION = 2
PROJECT_TYPE = "DCM_PROJECT"
DEFAULT_TARGET = "DCM_DEV"

ACCOUNT_IDENTIFIER = "KIPI-KIPI_PRIMARY"

WAREHOUSE = "DISHA_RANI_WH"
WH_SIZE = "XSMALL"

DCM_SCHEMA = "UTILITIES"
BASE_DATABASE = "CICD_demo_AUTOMATION"

ENVIRONMENTS = [
    "DEV",
    "QA",
    "PROD",
]

SCHEMAS = [
    "HOSPITALS",
    "PATIENTS",
    "UTILITIES",
]

# First role is used as project_owner
ROLES = {
    "DEV": [
        "GITHUB_CICD_DEMO_ROLE",
    ],
    "QA": [
        "GITHUB_CICD_DEMO_ROLE",
    ],
    "PROD": [
        "GITHUB_CICD_DEMO_ROLE",
    ],
}

DEFAULT_ROLES = [
    "GITHUB_CICD_DEMO_ROLE",
]


# ============================================================
# PATH RESOLUTION
# ============================================================

def get_project_root():
    try:
        start = Path(__file__).resolve().parent
    except NameError:
        start = Path.cwd()

    for directory in [start] + list(start.parents):
        candidate = directory / "dcm_automation_demo"
        if candidate.exists() and (candidate / "sources").exists():
            return candidate

    raise RuntimeError(
        "Could not locate dcm_automation_demo/ directory with sources/. "
        "Run the script from within the project workspace."
    )


# ============================================================
# BUILD MANIFEST
# ============================================================

def build_manifest():
    targets = {}
    configurations = {}

    for env in ENVIRONMENTS:
        database = f"{BASE_DATABASE}_{env}"
        project_name = f"{database}.{DCM_SCHEMA}.dcm_automation_demo"
        target_name = f"DCM_{env}"

        env_roles = ROLES.get(env, DEFAULT_ROLES)
        project_owner = env_roles[0]

        targets[target_name] = {
            "account_identifier": ACCOUNT_IDENTIFIER,
            "project_name": project_name,
            "project_owner": project_owner,
            "templating_config": env,
        }

        configurations[env] = {
            "env_suffix": f"_{env}",
            "database": database,
            "schemas": SCHEMAS,
            "dcm_schema": DCM_SCHEMA,
            "project_name": project_name,
            "project_owner": project_owner,
            "roles": env_roles,
        }

    return {
        "manifest_version": MANIFEST_VERSION,
        "type": PROJECT_TYPE,
        "default_target": DEFAULT_TARGET,
        "targets": targets,
        "templating": {
            "defaults": {
                "project_owner_role": DEFAULT_ROLES[0],
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

def write_manifest(manifest, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        yaml.dump(
            manifest,
            file,
            Dumper=NoAliasDumper,
            default_flow_style=False,
            sort_keys=False,
        )




# ============================================================
# MAIN
# ============================================================

def main():
    project_root = get_project_root()
    manifest = build_manifest()

    # Write manifest.yml inside dcm_automation_demo/ (same level as sources/)
    manifest_path = project_root / "manifest.yml"
    write_manifest(manifest, manifest_path)

    print("=" * 60)
    print("Manifest generated successfully.")
    print(f"Location: {manifest_path}")
    print("=" * 60)
    print()
    print(
        yaml.dump(
            manifest,
            Dumper=NoAliasDumper,
            default_flow_style=False,
            sort_keys=False,
        )
    )


main()
