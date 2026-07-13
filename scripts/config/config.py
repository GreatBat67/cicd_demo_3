from pathlib import Path
import yaml


class ConfigLoader:
    """Load configuration from project_config.yml."""

    def __init__(self, config_file="project_config.yml"):

        # ----------------------------------------------------
        # Locate config directory
        # ----------------------------------------------------

        try:
            # Running as a Python script
            base_dir = Path(__file__).resolve().parent

        except NameError:
            # Running in Notebook/Jupyter
            current = Path.cwd().resolve()

            base_dir = None

            for parent in [current] + list(current.parents):

                candidate = parent / "config"

                if (
                    candidate.exists()
                    and (candidate / config_file).exists()
                ):
                    base_dir = candidate
                    break

            if base_dir is None:
                raise RuntimeError(
                    f"Could not locate '{config_file}'."
                )

        self.base_dir = base_dir
        self.config_file = base_dir / config_file

        # ----------------------------------------------------
        # Read configuration
        # ----------------------------------------------------

        if not self.config_file.exists():
            raise FileNotFoundError(self.config_file)

        with self.config_file.open(
            "r",
            encoding="utf-8",
        ) as f:

            self._config = yaml.safe_load(f) or {}

    # ========================================================
    # Properties
    # ========================================================

    @property
    def project(self):
        return self._config.get("project", {})

    @property
    def snowflake(self):
        return self._config.get("snowflake", {})

    @property
    def databases(self):
        return self._config.get("databases", [])

    @property
    def schemas(self):
        return self._config.get("schemas", [])

    @property
    def roles(self):
        return self._config.get("roles", {})

    @property
    def dcm_project(self):
        return self._config.get("dcm_project", {})

    @property
    def dbt(self):
        return self._config.get("dbt", {})


# ============================================================
# LOAD CONFIG
# ============================================================

config = ConfigLoader()

PROJECT = config.project
PROJECT_NAME = PROJECT.get("name")

SNOWFLAKE = config.snowflake
DATABASES = config.databases
SCHEMAS = config.schemas
ROLES = config.roles
DCM_PROJECT = config.dcm_project

ADMIN_ROLE = SNOWFLAKE.get("admin_role")
ACCOUNT_IDENTIFIER = SNOWFLAKE.get("account_identifier")
WAREHOUSE = SNOWFLAKE.get("warehouse")
WAREHOUSE_SIZE = SNOWFLAKE.get("warehouse_size")

USER = SNOWFLAKE.get("user")
THREADS = SNOWFLAKE.get("threads")
client_session_keep_alive = SNOWFLAKE.get("client_session_keep_alive")


DCM_PROJECT = config.dcm_project
DBT = config.dbt
DBT_PROFILE_NAME = DBT.get("profile_name")
DBT_DEFAULT_TARGET = DBT.get("default_target")
DBT_TARGET_PREFIX = DBT.get("target_prefix")

DBT_PROJECT = DBT.get("project", {})
DBT_PROJECT_SCHEMA = DBT_PROJECT.get("schema")
DBT_PROJECT_OWNER_ROLE = DBT_PROJECT.get("owner_role")

DBT_TARGETS = DBT.get("targets", {})
DBT_SCHEMAS = sorted(
    {
        target["schema"]
        for target in DBT_TARGETS.values()
    }
)

# ============================================================
# DIRECTORY STRUCTURE
# ============================================================

SCRIPTS_DIR = config.base_dir.parent

# logs/ (inside scripts)
LOGS_DIR = SCRIPTS_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# workspace/ (parent of scripts)
WORKSPACE_DIR = SCRIPTS_DIR.parent
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DBT_PROJECT_DIR = WORKSPACE_DIR / DBT_PROFILE_NAME
DBT_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Locate DCM project
# ------------------------------------------------------------

PROJECT_DIR = None

for child in WORKSPACE_DIR.iterdir():

    if (
        child.is_dir()
        and child.name.lower() == PROJECT_NAME.lower()
    ):
        PROJECT_DIR = child.resolve()
        break

if PROJECT_DIR is None:
    raise RuntimeError(
        f"Could not locate project '{PROJECT_NAME}'."
    )

MANIFEST_FILE = PROJECT_DIR / "manifest.yml"

MACROS_DIR = PROJECT_DIR / "sources" / "macros"
MACROS_DIR.mkdir(parents=True, exist_ok=True)

DEFINITIONS_DIR = PROJECT_DIR / "sources" / "definitions"
DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# DEBUG
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CONFIGURATION")
    print("=" * 60)

    print("Config File      :", config.config_file)
    print("Scripts Dir      :", SCRIPTS_DIR)
    print("Workspace Dir    :", WORKSPACE_DIR)
    print("Logs Dir         :", LOGS_DIR)
    print("Project Dir      :", PROJECT_DIR)
    print("Manifest         :", MANIFEST_FILE)
    print("Macros           :", MACROS_DIR)
    print("Definitions      :", DEFINITIONS_DIR)
    print("dbt              :", DBT_PROJECT_DIR)
    print("dbt_schemas     :", DBT_SCHEMAS)

    print("=" * 60)