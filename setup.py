import os
import base64
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "kipibi"
REPO_NAME = "CI_CD_STANDARD_TIER_OFFERING_TEMPLATE"

if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN environment variable is missing!")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# ==============================================================================
# ENTERPRISE PIPELINE WITH AUTO-REVIEWER ASSIGNMENT
# ==============================================================================
WORKFLOW_YAML_CONTENT = r"""name: "Standard Tier: Automated Snowflake Delivery -new creds"

on:
  workflow_dispatch:
  pull_request:
    types: [opened, synchronize]
    branches: [cicd, prod]
    paths: ['dcm_automation/**', 'dcm_dbt_cicd/**']
  push:
    branches: [cicd, prod]
    paths: ['dcm_automation/**', 'dcm_dbt_cicd/**']

permissions:
  id-token: write 
  contents: read
  pull-requests: write # 🔐 Crucial: Gives the runner permission to assign reviewers via GitHub CLI

env:
  # Shared Global Connection Parameters
  SNOWFLAKE_ACCOUNT: "KIPI-KIPI_PRIMARY"
  SNOWFLAKE_ROLE: "github_cicd_demo_role"
  SNOWFLAKE_WAREHOUSE: "github_cicd_demo_wh"
  SNOWFLAKE_CLI_FEATURES_ENABLE_SNOWFLAKE_PROJECTS: "true"

jobs:
  # ==========================================================
  # 🛠️ STAGE 1: THE CICD / STAGING GATE (dev ➔ cicd)
  # ==========================================================
  cicd-environment-plan:
    if: github.event_name == 'pull_request' && github.base_ref == 'cicd'
    runs-on: ubuntu-latest
    environment: cicd 
    env:
      SNOWFLAKE_USER: "github_cicd_demo_cicd_user" 
      SNOWFLAKE_DATABASE: "CICD_DEMO_AUTOMATION"
      SNOWFLAKE_SCHEMA: "DCM_SILVER"
    steps:
      - uses: actions/checkout@v4

      - name: Assign DishaRaniBR as Official Reviewer
        env:
          GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
          REVIEWER: "DishaRaniBR"
        run: |
          echo "📥 Dynamically assigning $REVIEWER to Staging PR #${{ github.event.pull_request.number }}..."
          gh pr edit ${{ github.event.pull_request.number }} --add-reviewer "$REVIEWER"

      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true

      - name: Run DCM Plan Against CICD Staging
        run: |
          echo "🔍 Running DCM infrastructure validation..."
          cd dcm_automation
          snow dcm plan --target DCM_PROD -x
          cd ..
          echo "Building test environment for dbt transformations..."
          snow dbt deploy dbt_project_dev --source ./dcm_dbt_cicd --force -x

  cicd-environment-deploy:
    if: github.event_name == 'push' && github.ref_name == 'cicd'
    runs-on: ubuntu-latest
    environment: cicd 
    env:
      SNOWFLAKE_USER: "github_cicd_demo_cicd_user"
      SNOWFLAKE_DATABASE: "CICD_DEMO_AUTOMATION"
      SNOWFLAKE_SCHEMA: "DCM_SILVER"
    steps:
      - uses: actions/checkout@v4
      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true
      - name: Live Deploy to CICD Automation Database
        run: |
          echo "🚀 LIVE: Processing automated DCM infrastructure deployment..."
          cd dcm_automation
          snow dcm deploy --target DCM_PROD -x
          cd ..
          echo "🚀 LIVE: Synchronizing and running staging dbt project..."
          snow dbt deploy dbt_project_prod --source ./dcm_dbt_cicd --force -x
          snow dbt execute -x dbt_project_prod run --target DCM_PROD

  # ==========================================================
  # 🚀 STAGE 2: THE PRODUCTION GATE (cicd ➔ prod)
  # ==========================================================
  production-environment-plan:
    if: github.event_name == 'pull_request' && github.base_ref == 'prod'
    runs-on: ubuntu-latest
    environment: prod 
    env:
      SNOWFLAKE_USER: "github_cicd_demo_prod_user" 
      SNOWFLAKE_DATABASE: "CICD_DEMO_PROD"
      SNOWFLAKE_SCHEMA: "DCM_SILVER"
    steps:
      - uses: actions/checkout@v4

      - name: Assign DishaRaniBR as Official Reviewer
        env:
          GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
          REVIEWER: "DishaRaniBR"
        run: |
          echo "📥 Dynamically assigning $REVIEWER to Production PR #${{ github.event.pull_request.number }}..."
          gh pr edit ${{ github.event.pull_request.number }} --add-reviewer "$REVIEWER"

      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true

      - name: Run DCM Plan Against Production
        run: |
          echo "🔍 Running DCM infrastructure validation..."
          cd dcm_automation
          snow dcm plan --target DCM_PROD -x
          cd ..
          echo "Building test environment for dbt transformations..."
          snow dbt deploy dbt_project_dev --source ./dcm_dbt_cicd --force -x

  production-environment-deploy:
    if: github.event_name == 'push' && github.ref_name == 'prod'
    runs-on: ubuntu-latest
    environment: prod 
    env:
      SNOWFLAKE_USER: "github_cicd_demo_prod_user"
      SNOWFLAKE_DATABASE: "CICD_DEMO_PROD"
      SNOWFLAKE_SCHEMA: "DCM_SILVER"
    steps:
      - uses: actions/checkout@v4
      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true
      - name: Live Deploy to Production Target
        run: |
          echo "🚀 LIVE: Processing automated DCM infrastructure deployment..."
          cd dcm_automation
          snow dcm deploy --target DCM_PROD -x
          cd ..
          echo "🚀 LIVE: Synchronizing and running production dbt project..."
          snow dbt deploy dbt_project_prod --source ./dcm_dbt_cicd --force -x
          snow dbt execute -x dbt_project_prod run --target DCM_PROD
"""

def get_baseline_branch_sha():
    url = f"{BASE_URL}/git/ref/heads/main"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["object"]["sha"]
    else:
        raise Exception(f"Failed to communicate with repository baseline: {response.text}")

def create_target_branch(branch_name, base_sha):
    url = f"{BASE_URL}/git/refs"
    payload = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 201:
        print(f"✅ Success: Branch '{branch_name}' synchronized successfully.")
    elif response.status_code == 422:
        print(f"ℹ️ Notice: Branch '{branch_name}' already exists. Preserving current state.")
    else:
        print(f"❌ Error creating branch '{branch_name}': {response.text}")

def inject_workflow_payload():
    path = ".github/workflows/dcm-ci.yml"
    url = f"{BASE_URL}/contents/{path}"
    
    sha = None
    get_file = requests.get(url, headers=HEADERS)
    if get_file.status_code == 200:
        sha = get_file.json()["sha"]
        
    encoded_content = base64.b64encode(WORKFLOW_YAML_CONTENT.encode("utf-8")).decode("utf-8")
    payload = {
        "message": "ci: implement automated reviewer routing engine for gating tracks",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    response = requests.put(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 201]:
        print(f"✅ Success: Gated multi-environment assignment pipeline live at '{path}'.")
    else:
        print(f"❌ Error injecting workflow file: {response.text}")

if __name__ == "__main__":
    print(f"🚀 Initializing Gated Environment Architecture for {REPO_OWNER}/{REPO_NAME}...")
    try:
        base_sha = get_baseline_branch_sha()
        for branch in ["dev", "cicd", "prod"]:
            create_target_branch(branch, base_sha)
        inject_workflow_payload()
        print("\n🎉 Setup complete! Run 'git pull origin dev' locally to fetch your workflow upgrades.")
    except Exception as e:
        print(f"\n❌ Execution halted: {str(e)}")
