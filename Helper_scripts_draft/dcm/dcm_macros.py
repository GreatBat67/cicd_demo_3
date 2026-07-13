# DCM macro generator with dynamic role support
from pathlib import Path
import json

# ============================================================
# CONFIG
# ============================================================

PROJECT_OWNER_ROLE = "GITHUB_CICD_DEMO_ROLE"

ENV_CONFIG = {
    "_DEV": {
        "database": "CICD_AUTOMATION_DEV",
        "schemas": ["HOSPITALS", "PATIENTS", "UTILITIES"],
        "roles": {
            "owner": "project_owner_role",
            # "developer": "project_developer_role_dev",
            # "analyst": "project_analyst_role_dev",
        },
    },
    "_QA": {
        "database": "CICD_AUTOMATION_QA",
        "schemas": ["HOSPITALS", "PATIENTS", "UTILITIES"],
        "roles": {
            "owner": "project_owner_role",
        },
    },
    "_PROD": {
        "database": "CICD_AUTOMATION_PROD",
        "schemas": ["HOSPITALS", "PATIENTS", "UTILITIES"],
        "roles": {
            "owner": "project_owner_role",
        },
    },
}

ROLE_POLICY = {
    "owner": {
        "create": True,
        "ownership": True,
        "read": True,
    },
    "developer": {
        "create": True,
        "ownership": False,
        "read": True,
    },
    "analyst": {
        "create": False,
        "ownership": False,
        "read": True,
    },
}

SCHEMA_CREATE_GRANTS = [
    "CREATE TABLE",
    "CREATE VIEW",
    "CREATE STAGE",
    "CREATE STREAM",
    "CREATE FILE FORMAT",
    "CREATE TASK",
]

FUTURE_GRANT_OBJECT_TYPES = [
    "TABLES",
    "VIEWS",
    "STAGES",
    "STREAMS",
    "FILE FORMATS",
    "SEQUENCES",
    "PROCEDURES",
    "FUNCTIONS",
]

# ============================================================
# VALIDATION: ensure every role_type in ENV_CONFIG has a policy
# ============================================================

def validate_config():
    all_role_types = set()
    for env_suffix, cfg in ENV_CONFIG.items():
        for role_type in cfg.get("roles", {}):
            all_role_types.add(role_type)

    missing = all_role_types - set(ROLE_POLICY.keys())
    if missing:
        raise ValueError(
            f"ROLE_POLICY is missing definitions for role types used in ENV_CONFIG: {missing}. "
            f"Add entries to ROLE_POLICY with 'create', 'ownership', and 'read' flags."
        )

validate_config()

# ============================================================
# PATH RESOLUTION
# ============================================================

current = Path.cwd()

workspace_root = None
for parent in [current] + list(current.parents):
    if (parent / "dcm_automation").exists():
        workspace_root = parent
        break

if workspace_root is None:
    raise RuntimeError("Could not locate dcm_automation project.")

MACROS_DIR = workspace_root / "dcm_automation" / "sources" / "macros"
MACROS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# GENERATE MACRO 
# ============================================================

def generate_grants_macro():
    return f"""
{{% macro create_dcm_project(env_config, project_owner_role) %}}

-- ======================================================
-- RBAC 
-- ======================================================

{{% for env_suffix, cfg in env_config.items() %}}

-- ======================================================
-- ENV: {{{{ env_suffix }}}}
-- ======================================================

{{% set db = cfg.database %}}
{{% set schemas = cfg.schemas %}}
{{% set roles = cfg.roles %}}

{{% for role_type, role_name in roles.items() %}}

-- ------------------------------------------------------
-- ROLE: {{{{ role_type }}}} ({{{{ role_name }}}})
-- ------------------------------------------------------

{{% for schema in schemas %}}

{{% set full_schema = db ~ "." ~ schema %}}

-- Base Access
GRANT USAGE ON DATABASE {{{{ db }}}} TO ROLE {{{{ role_name }}}};
GRANT USAGE ON SCHEMA {{{{ full_schema }}}} TO ROLE {{{{ role_name }}}};

-- Create Privileges
{{% if ROLE_POLICY[role_type].create %}}
GRANT {", ".join(SCHEMA_CREATE_GRANTS)}
ON SCHEMA {{{{ full_schema }}}}
TO ROLE {{{{ role_name }}}};
{{% endif %}}

-- Read Access
{{% if ROLE_POLICY[role_type].read %}}
GRANT SELECT ON ALL TABLES IN SCHEMA {{{{ full_schema }}}} TO ROLE {{{{ role_name }}}};
GRANT SELECT ON FUTURE TABLES IN SCHEMA {{{{ full_schema }}}} TO ROLE {{{{ role_name }}}};
{{% endif %}}

-- Ownership
{{% if ROLE_POLICY[role_type].ownership %}}
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA {{{{ full_schema }}}}
TO ROLE {{{{ role_name }}}}
COPY CURRENT GRANTS;

{{% for obj in FUTURE_GRANT_OBJECT_TYPES %}}
GRANT OWNERSHIP ON FUTURE {{{{ obj }}}}
IN SCHEMA {{{{ full_schema }}}}
TO ROLE {{{{ role_name }}}};
{{% endfor %}}
{{% endif %}}

{{% endfor %}}

{{% endfor %}}

-- Role hierarchy
{{% set role_list = roles.values() | list %}}

{{% for i in range(role_list | length - 1) %}}
GRANT ROLE {{{{ role_list[i] }}}} TO ROLE {{{{ role_list[i+1] }}}};
{{% endfor %}}

GRANT ROLE {{{{ role_list[-1] }}}} TO ROLE {{{{ project_owner_role }}}};

{{% endfor %}}

{{% endmacro %}}
"""

# ============================================================
# DEMO 
# ============================================================

def generate_jinja_demo():
    return """-- Execute RBAC macro

{{ create_dcm_project(ENV_CONFIG, PROJECT_OWNER_ROLE) }}
"""

# ============================================================
# WRITE FILES
# ============================================================

grants_path = MACROS_DIR / "grants_macro.sql"
grants_path.write_text(generate_grants_macro(), encoding="utf-8")
print(f"WROTE: {grants_path}")

jinja_demo_path = MACROS_DIR / "jinja_demo.sql"
jinja_demo_path.write_text(generate_jinja_demo(), encoding="utf-8")
print(f"WROTE: {jinja_demo_path}")

print("\nMacros generation complete.")