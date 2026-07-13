# Setup generalized, variable-tier GitHub branch protection, environments, secrets, and Snowflake deployment workflows dynamically
"""
Usage (Headless Configuration Mode):
    python consolidates.py --input-file pipeline_inputs.yaml

Usage (Auto-Detect YAML Mode):
    python consolidates.py

Requirements:
    pip install PyGithub PyYAML requests pynacl
"""

import argparse
import os
import sys
import yaml
import requests
from github import Github, GithubException


def interactive_wizard():
    """Interactive runtime CLI engine to dynamically discover repository topology and credentials."""
    print("\n" + "="*60)
    print("   DYNAMIC MULTI-TIER REPOSITORY ARCHITECTURE WIZARD")
    print("="*60 + "\n")

    inputs = {}

    # 1. Global Repository Metadata
    inputs['owner'] = input("Enter GitHub Username or Org Name (e.g., GreatBat67): ").strip()
    inputs['repo_name'] = input("Enter Repository Name (e.g., cocothon): ").strip()
    inputs['project_name'] = input("Enter Project Description: ").strip() or "Dynamic Gated Architecture"

    # 2. Path Filters
    paths_raw = input("\nEnter comma-separated paths to monitor (default: dcm_automation/**,dcm_dbt_cicd/**): ").strip()
    inputs['paths'] = [p.strip() for p in paths_raw.split(',')] if paths_raw else ['dcm_automation/**', 'dcm_dbt_cicd/**']

    # 3. Global Snowflake Core Parameters
    print("\n--- Global Snowflake Infrastructure Configuration ---")
    inputs['sf_account'] = input("Enter SNOWFLAKE_ACCOUNT locator (e.g., KIPI-KIPI_PRIMARY): ").strip()
    inputs['sf_role'] = input("Enter SNOWFLAKE_ROLE (e.g., github_cicd_demo_role): ").strip()
    inputs['sf_warehouse'] = input("Enter SNOWFLAKE_WAREHOUSE (e.g., github_cicd_demo_wh): ").strip()

    # 4. Dynamic Branch Sequence Discovery
    print("\n--- Dynamic Branch Sequence Definition ---")
    print("Define your branch sequence in order from lowest environment to highest environment.")
    print("Example 1 (Simple): dev, main")
    print("Example 2 (Standard): dev, qa, cicd, main")
    
    branches_raw = input("\nEnter comma-separated branch names in progression order: ").strip()
    if not branches_raw:
        print("Error: You must specify at least two branches to build a progression gate.")
        sys.exit(1)
        
    inputs['branch_sequence'] = [b.strip() for b in branches_raw.split(',')]
    if len(inputs['branch_sequence']) < 2:
        print("Error: A minimum of 2 sequential branches is required.")
        sys.exit(1)

    # 5. Iterative Per-Branch Configuration Mapping
    inputs['branch_data'] = {}
    any_email_gate = False

    for idx, b in enumerate(inputs['branch_sequence']):
        print(f"\n--- Configure Branch Context: [{b}] ---")
        b_data = {}
        
        if idx == 0:
            b_data['require_pr'] = False
            b_data['required_approvals'] = 0
            b_data['approvers'] = []
            print(f"  -> '{b}' identified as baseline branch. Direct pushes allowed, tracking gates initialized.")
        else:
            pr_choice = input(f"Does branch '{b}' require a Pull Request to merge? (y/n, default: y): ").strip().lower()
            if pr_choice == 'n':
                b_data['require_pr'] = False
                b_data['required_approvals'] = 0
                b_data['approvers'] = []
            else:
                b_data['require_pr'] = True
                b_data['required_approvals'] = 1
                b_data['approvers'] = [u.strip() for u in input(f"  Enter comma-separated GitHub usernames for '{b}' reviewers: ").split(',') if u.strip()]

        sf_choice = input(f"Does code hitting '{b}' deploy/plan against a Snowflake target database? (y/n, default: y): ").strip().lower()
        if sf_choice == 'n':
            b_data['has_snowflake'] = False
        else:
            b_data['has_snowflake'] = True
            b_data['sf_user'] = input(f"  Enter Snowflake User for {b}: ").strip()
            b_data['sf_db'] = input(f"  Enter Snowflake Target Database for {b}: ").strip()
            b_data['sf_schema'] = input(f"  Enter Snowflake Target Schema for {b} (default: UTILITIES): ").strip() or "UTILITIES"
            b_data['dcm_target'] = input(f"  Enter DCM target identifier flag for {b} (e.g., DCM_QA, DCM_PROD): ").strip()

        gate_choice = input(f"Does branch '{b}' require a Business Email Approval loop before merging/deploying? (y/n, default: n): ").strip().lower()
        if gate_choice == 'y':
            b_data['has_email_gate'] = True
            any_email_gate = True
        else:
            b_data['has_email_gate'] = False

        inputs['branch_data'][b] = b_data

    if any_email_gate:
        print("\n--- Business Release Gate Details & Credentials ---")
        inputs['biz_email'] = input("Enter stakeholder sign-off destination email address: ").strip()
        inputs['imap_server'] = input("Enter corporate IMAP verification email server (e.g., imap.gmail.com): ").strip()
        print("\n[SECRET MATRIX] Cryptographic credential sync initialized:")
        inputs['imap_user'] = input("  Enter IMAP Secret Username: ").strip()
        inputs['imap_pass'] = input("  Enter IMAP Secret Password/App-Password: ").strip()

    return inputs


def compile_yaml_config_structure(inputs):
    """Assembles an adaptive dictionary layout matching the user's custom branch list."""
    config = {
        "repo_name": inputs['repo_name'],
        "owner": inputs['owner'],
        "project_name": inputs['project_name'],
        "default_branch": inputs['default_branch'],
        "branches": {}
    }
    
    for idx, b in enumerate(inputs['branch_sequence']):
        b_inputs = inputs['branch_data'][b]
        is_last = (idx == len(inputs['branch_sequence']) - 1)
        
        b_cfg = {
            "protection": {
                "require_pr": b_inputs['require_pr'],
                "required_approvals": b_inputs['required_approvals']
            },
            "approvers": {"groups": [], "individuals": b_inputs['approvers']},
            "environment": b if b_inputs['has_snowflake'] else None,
            "environment_reviewers": {"groups": [], "individuals": b_inputs['approvers'] if b_inputs['has_snowflake'] else []}
        }
        
        if idx > 0:
            b_cfg["source_branch"] = inputs['branch_sequence'][idx - 1]
            
        if is_last:
            b_cfg["locked"] = True
            b_cfg["protection"]["lock_branch"] = True
            b_cfg["protection"]["restrict_pushes"] = True
            
        config["branches"][b] = b_cfg
        
    return config


# ==========================================================
# 📋 POLYMORPHIC WORKFLOW STRING INTERPOLATION GENERATORS
# ==========================================================

def generate_dynamic_pr_gate_yml(inputs):
    """Generates a sequential transition checker tailored to the custom branch sequence."""
    workflow = """# Adaptive One-way PR gate enforcement workflow
name: Enforce One-Way PR Gate
on:
  pull_request:
    types: [opened, reopened, synchronize, edited]
    branches:"""
    
    for b in inputs['branch_sequence'][1:]:
        workflow += f"\n      - {b}"
        
    workflow += """

jobs:
  gate-check:
    runs-on: ubuntu-latest
    steps:"""
    
    for idx in range(1, len(inputs['branch_sequence'])):
        target = inputs['branch_sequence'][idx]
        source = inputs['branch_sequence'][idx - 1]
        
        workflow += f"""
      - name: Enforce {source} -> {target} gate
        if: github.event.pull_request.base.ref == '{target}' && github.event.pull_request.head.ref != '{source}'
        run: |
          echo "::error::PR routing violation. Merges into target branch '{target}' must originate from source branch '{source}'."
          exit 1"""
          
    workflow += """
      - name: Gate passed
        run: echo "Branch pipeline trajectory validated successfully."
"""
    return workflow


def generate_dynamic_master_delivery_yml(inputs):
    """Builds a centralized entry router managing custom paths, triggers, and targets."""
    paths_str = "\n".join([f"      - '{p}'" for p in inputs['paths']])
    branches_str = "\n".join([f"      - {b}" for b in inputs['branch_sequence'][1:]])
    
    template = """name: "Standard Tier: Automated Snowflake Delivery - Master"
on:
  workflow_dispatch:
  pull_request:
    types: [opened, synchronize]
    branches:
<BRANCHES_STR>
    paths:
<PATHS_STR>
  push:
    branches:
<BRANCHES_STR>
    paths:
<PATHS_STR>

permissions:
  id-token: write 
  contents: read

jobs:"""

    workflow = template.replace("<BRANCHES_STR>", branches_str).replace("<PATHS_STR>", paths_str)

    for b in inputs['branch_sequence']:
        b_inputs = inputs['branch_data'][b]
        
        if b_inputs['has_email_gate']:
            workflow += f"""
  {b}-business-approval-gate:
    if: github.base_ref == '{b}' && github.event_name == 'pull_request'
    uses: ./.github/workflows/business-email-gate-{b}.yml
    secrets: inherit"""
            
        if b_inputs['has_snowflake']:
            if b_inputs['has_email_gate']:
                condition_str = f"github.ref_name == '{b}' && github.event_name == 'push'"
            else:
                condition_str = f"(github.base_ref == '{b}' && github.event_name == 'pull_request') || (github.ref_name == '{b}' && github.event_name == 'push')"
                
            workflow += f"""
  {b}-snowflake-pipeline:
    if: {condition_str}"""
            if b_inputs['has_email_gate']:
                workflow += f"\n    needs: {b}-business-approval-gate"
                
            workflow += f"""
    uses: ./.github/workflows/snowflake-pipeline-{b}.yml
    secrets: inherit"""
            
    return workflow


def generate_dynamic_branch_pipeline_yml(b_name, b_inputs, inputs):
    """Creates an isolated reusable component pipeline with unique server credentials."""
    template = """name: "Snowflake Component: Progression Target - <B_NAME>"
on:
  workflow_call:

env:
  SNOWFLAKE_ACCOUNT: "<SF_ACCOUNT>"
  SNOWFLAKE_ROLE: "<SF_ROLE>"
  SNOWFLAKE_WAREHOUSE: "<SF_WAREHOUSE>"
  SNOWFLAKE_CLI_FEATURES_ENABLE_SNOWFLAKE_PROJECTS: "true"
  SNOWFLAKE_DATABASE: "<SF_DB>"
  SNOWFLAKE_SCHEMA: "<SF_SCHEMA>"

jobs:
  <B_NAME>-environment-plan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    environment: <B_NAME> 
    steps:
      - uses: actions/checkout@v4
      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true
      - name: Run DCM Plan Against Target
        run: |
          echo "Running DCM infrastructure validation mapping..."
          cd dcm_automation
          snow dcm plan --target <DCM_TARGET> -x
          cd ..
          echo "Building test environment for dbt transformations..."
          snow dbt deploy dbt_project_dev --source ./dcm_dbt_cicd --force -x

  <B_NAME>-environment-deploy:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: <B_NAME> 
    steps:
      - uses: actions/checkout@v4
      - name: Setup Snowflake CLI (OIDC)
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true
      - name: Live Deploy to Database Target
        run: |
          echo "LIVE: Processing automated DCM infrastructure deployment..."
          cd dcm_automation
          snow dcm deploy --target <DCM_TARGET> -x
          cd ..
          echo "LIVE: Synchronizing and running targeted dbt project models..."
          snow dbt deploy dbt_project_prod --source ./dcm_dbt_cicd --force -x
          snow dbt execute -x dbt_project_prod run --target <DCM_TARGET>
"""
    return (template
            .replace("<B_NAME>", b_name)
            .replace("<SF_ACCOUNT>", inputs['sf_account'])
            .replace("<SF_ROLE>", inputs['sf_role'])
            .replace("<SF_WAREHOUSE>", inputs['sf_warehouse'])
            .replace("<SF_USER>", b_inputs['sf_user'])
            .replace("<SF_DB>", b_inputs['sf_db'])
            .replace("<SF_SCHEMA>", b_inputs['sf_schema'])
            .replace("<DCM_TARGET>", b_inputs['dcm_target']))


def generate_dynamic_business_gate_yml(b_name, b_inputs, inputs):
    template = """name: "Release Gate: Business Email Verification - <B_NAME>"
on:
  workflow_call:

jobs:
  email-verification:
    runs-on: ubuntu-latest
    steps:
      - name: Dispatch Notification Email
        run: |
          echo "Sending Release Sign-off Verification Alert out to Stakeholder Team..."
          echo "Target Address: <BIZ_EMAIL>"
          echo "Subject Parameter Validation: GH_RUN_ID:${{ github.run_id }}"

      - name: Poll Mailbox for Approval Sign-off
        shell: python
        run: |
          import imaplib, email, time, sys
          
          IMAP_SERVER = "<IMAP_SERVER>"
          EMAIL_USER = "${{ secrets.BUSINESS_GATE_IMAP_USER }}"
          EMAIL_PASS = "${{ secrets.BUSINESS_GATE_IMAP_PASSWORD }}"
          RUN_ID = "${{ github.run_id }}"
          
          print(f"Starting asynchronous validation loop tracking Run ID identifier: [GH_RUN_ID:{RUN_ID}]")
          timeout_limit = 900 
          polling_interval = 30
          elapsed = 0
          
          while elapsed < timeout_limit:
              try:
                  mail = imaplib.IMAP4_SSL(IMAP_SERVER)
                  mail.login(EMAIL_USER, EMAIL_PASS)
                  mail.select("inbox")
                  
                  status, data = mail.search(None, f'(SUBJECT "GH_RUN_ID:{RUN_ID}")')
                  if status == "OK" and data[0]:
                      for message_num in data[0].split():
                          status, msg_data = mail.fetch(message_num, "(RFC822)")
                          msg = email.message_from_bytes(msg_data[0][1])
                          
                          body_payload = ""
                          if msg.is_multipart():
                              for segment in msg.walk():
                                  if segment.get_content_type() == "text/plain":
                                      body_payload += segment.get_payload(decode=True).decode()
                          else:
                              body_payload = msg.get_payload(decode=True).decode()
                          
                          parsed_payload = body_payload.upper()
                          if "APPROVED" in parsed_payload:
                              print("Business Approval confirmation found! Releasing gate.")
                              sys.exit(0)
                          elif "REJECTED" in parsed_payload:
                              print("Release explicitly REJECTED by business team.")
                              sys.exit(1)
                  mail.logout()
              except Exception as error:
                  print(f"Connection/Polling Check Event Error: {error}")
                  
              time.sleep(polling_interval)
              elapsed += polling_interval
              
          print("Timeout limit reached without receiving valid business authorization.")
          sys.exit(1)
"""
    return (template
            .replace("<B_NAME>", b_name)
            .replace("<BIZ_EMAIL>", inputs.get('biz_email', ''))
            .replace("<IMAP_SERVER>", inputs.get('imap_server', '')))


# ==========================================================
# 🛠️ GITHUB REPOSITORY MANIPULATION FUNCTIONS
# ==========================================================

def create_new_github_repository(g, owner, repo_name, description):
    print(f"  [CREATING] Initializing new PUBLIC repository '{owner}/{repo_name}' on GitHub...")
    try:
        try:
            entity = g.get_organization(owner)
        except GithubException:
            entity = g.get_user()

        repo = entity.create_repo(
            name=repo_name,
            description=description,
            private=False, 
            has_issues=True,
            has_wiki=False
        )
        print(f"  [SUCCESS] New PUBLIC repository '{owner}/{repo_name}' successfully created!")
        return repo
    except GithubException as e:
        print(f"CRITICAL ERROR: Failed to create repository automatically: {e}")
        sys.exit(1)


def initialize_empty_repo(repo, default_branch="main"):
    try:
        repo.get_branch(repo.default_branch)
        print(f"  [INIT] Repository already contains branch context ('{repo.default_branch}'). Proceeding.")
    except GithubException as e:
        if e.status == 404 or "Branch not found" in str(e):
            print(f"  [INIT] Empty repository discovered. Generating base commit to create '{default_branch}'...")
            try:
                repo.create_file(
                    path="README.md",
                    message="Initialize Repository Architecture",
                    content=f"# {repo.name}\nScaffolded Dynamic Gated Architecture Workflow Structure.",
                    branch=default_branch
                )
                print(f"  [INIT] Repository successfully initialized. Root anchor branch set to '{default_branch}'.")
            except GithubException as err:
                print(f"  [CRITICAL ERROR] Could not initialize cold-start file: {err}")
                sys.exit(1)
        else:
            print(f"  [CRITICAL ERROR] Unhandled validation error checking repository state: {e}")
            sys.exit(1)


def create_environment(repo, env_name, approvers_list, token):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    url = f"https://api.github.com/repos/{repo.full_name}/environments/{env_name}"
    
    reviewers = []
    g = Github(token)
    for username in approvers_list:
        try:
            user = g.get_user(username)
            reviewers.append({"type": "User", "id": user.id})
        except GithubException:
            print(f"  [WARNING] User '{username}' not found while configuring environment. Skipping.")

    payload = {}
    if reviewers:
        payload["reviewers"] = reviewers
        payload["deployment_branch_policy"] = {"protected_branches": False, "custom_branch_policies": True}

    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        print(f"  [ENVIRONMENT] GitHub Environment '{env_name}' created with {len(reviewers)} reviewer(s).")


def commit_file_to_github(repo, path, content, branch="dev"):
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(path, f"Regenerate execution pipeline profile: {path}", content, existing.sha, branch=branch)
        print(f"  [REMOTE SYNC] {path} updated on branch '{branch}'")
    except GithubException:
        repo.create_file(path, f"Scaffold unified architecture file: {path}", content, branch=branch)
        print(f"  [REMOTE SYNC] {path} initialized on branch '{branch}'")


def ensure_branch_exists(repo, branch_name, source_branch="main"):
    try:
        repo.get_branch(branch_name)
        print(f"  [EXISTS] Branch '{branch_name}' active.")
    except GithubException:
        source = repo.get_branch(source_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
        print(f"  [CREATED] Branch '{branch_name}' instantiated from '{source_branch}' reference.")


def lock_branch_via_api(repo, branch_name, token):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo.full_name}/branches/{branch_name}/protection"
    payload = {
        "required_status_checks": None,
        "enforce_admins": True,
        "required_pull_request_reviews": {"required_approving_review_count": 6, "dismiss_stale_reviews": True},
        "restrictions": None, "lock_branch": True, "allow_force_pushes": False, "allow_deletions": False
    }
    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code == 200:
        print(f"  [LOCKED] Target branch '{branch_name}' has been locked.")


def apply_branch_protection(repo, branch_name, branch_config, token):
    protection = branch_config.get("protection", {})
    is_locked = branch_config.get("locked", False)
    try:
        branch = repo.get_branch(branch_name)
        if protection.get("require_pr", False) or is_locked:
            branch.edit_protection(
                enforce_admins=protection.get("enforce_admins", True),
                dismiss_stale_reviews=protection.get("dismiss_stale_reviews", True),
                require_code_owner_reviews=protection.get("require_code_owner_reviews", False),
                required_approving_review_count=protection.get("required_approvals", 1),
            )
            print(f"  [RULESET] Protection rules applied to branch '{branch_name}'.")
            if is_locked:
                lock_branch_via_api(repo, branch_name, token)
        else:
            branch.edit_protection(enforce_admins=False, allow_force_pushes=False, allow_deletions=False)
            print(f"  [RULESET] Light protection applied to branch '{branch_name}'.")
    except GithubException as e:
        print(f"  [SKIPPED] Protection on '{branch_name}' skipped (requires public repo or premium GitHub tier): {e}")


def main():
    # Setup Named Configuration Argument Parsers
    parser = argparse.ArgumentParser(description="Autonomous Gated Architecture Orchestration Engine")
    parser.add_argument("--input-file", help="Path to pre-built YAML configuration input parameter file")
    args = parser.parse_args()

    # Paste your live token string between the quotes below
    token = "token"

    if not token or token.strip() == "":
        print("CRITICAL EXCEPTION: Token variable is completely empty inside the execution script.")
        sys.exit(1)

    # Resolve Inputs Matrix (File vs Auto-Detect vs Interactive Wizard fallback)
    if args.input_file:
        print(f"File-driven input mode initialized. Parsing configuration from: '{args.input_file}'...")
        if not os.path.exists(args.input_file):
            print(f"Error: Specified input configuration path '{args.input_file}' does not exist.")
            sys.exit(1)
        with open(args.input_file, "r") as f:
            inputs = yaml.safe_load(f)
        inputs['default_branch'] = inputs['branch_sequence'][0]
        inputs['final_branch'] = inputs['branch_sequence'][-1]
    elif os.path.exists("pipeline_inputs.yaml"):
        print("Auto-detected 'pipeline_inputs.yaml' in current execution path. Processing...")
        with open("pipeline_inputs.yaml", "r") as f:
            inputs = yaml.safe_load(f)
        inputs['default_branch'] = inputs['branch_sequence'][0]
        inputs['final_branch'] = inputs['branch_sequence'][-1]
    else:
        inputs = interactive_wizard()
        
    derived_yaml_config = compile_yaml_config_structure(inputs)
    
    g = Github(token)
    full_repo_path = f"{inputs['owner']}/{inputs['repo_name']}"
    
    try:
        repo = g.get_repo(full_repo_path)
    except GithubException as e:
        if e.status == 404:
            print(f"\nRepository '{full_repo_path}' was not found.")
            if args.input_file or os.path.exists("pipeline_inputs.yaml"):
                choice = 'y'
                print("Headless file mode triggered. Automatically provisioning missing public repository...")
            else:
                choice = input("Would you like to automatically create this repository on GitHub now as a PUBLIC repository? (y/n): ").strip().lower()
                
            if choice == 'y':
                repo = create_new_github_repository(g, inputs['owner'], inputs['repo_name'], inputs['project_name'])
            else:
                print("Setup aborted. Please create the repository manually and re-run the script.")
                sys.exit(1)
        else:
            print(f"Access denied or unhandled GitHub connection error: {e}")
            sys.exit(1)

    print("\n" + "="*60)
    print("   STARTING DEPLOYMENT GENERATION MATRIX")
    print("="*60)

    # Step 1: Cold Start Checks
    print("\n[1/8] Running Cold-Start Empty Repo Checks...")
    initialize_empty_repo(repo, default_branch="main")

    # Step 2: Adaptive Topology Sequencing
    print("\n[2/8] Generating Specified Branch Topology Sequence...")
    for b_name in inputs['branch_sequence']:
        if b_name != "main":
            ensure_branch_exists(repo, b_name, source_branch="main")

    # Step 3: Branch Pointer Matching
    print(f"\n[3/8] Syncing Default Repository Pointer to '{inputs['default_branch']}'...")
    if repo.default_branch != inputs['default_branch']:
        repo.edit(default_branch=inputs['default_branch'])

    # Step 4: Branch Governance Rulesets
    print("\n[4/8] Binding Branch Governance Rulesets...")
    for b_name, b_cfg in derived_yaml_config["branches"].items():
        apply_branch_protection(repo, b_name, b_cfg, token)

    # Step 5: Environment Gate Provisioning
    print("\n[5/8] Provisioning Custom GitHub Environments & Deployment Gates...")
    for b_name in inputs['branch_sequence']:
        b_inputs = inputs['branch_data'][b_name]
        if b_inputs['has_snowflake'] and b_inputs['approvers']:
            create_environment(repo, b_name, b_inputs['approvers'], token)

    # Step 6: GitHub Actions Secrets Cryptographic Upload
    any_email_gate = any(inputs['branch_data'][b].get('has_email_gate', False) for b in inputs['branch_sequence'])
    if any_email_gate:
        print("\n[6/8] Encrypting and Provisioning Repository Secrets...")
        try:
            repo.create_secret("BUSINESS_GATE_IMAP_USER", inputs['imap_user'])
            print("  [SECRET ENCRYPTED] 'BUSINESS_GATE_IMAP_USER' successfully added.")
            repo.create_secret("BUSINESS_GATE_IMAP_PASSWORD", inputs['imap_pass'])
            print("  [SECRET ENCRYPTED] 'BUSINESS_GATE_IMAP_PASSWORD' successfully added.")
        except Exception as err:
            print(f"  [WARNING] Failed to run cryptographic secrets generation: {err}")
    else:
        print("\n[6/8] Skipping Secret Provisioning (No email authorization gate requested).")

    # Step 7: Spec Sheet Local Archive
    print("\n[7/8] Archiving Automated Config Specs...")
    local_config_filename = "github_gates_config.yaml"
    with open(local_config_filename, "w") as f:
        yaml.dump(derived_yaml_config, f, default_flow_style=False, sort_keys=False)
    print(f"  [LOCAL] Saved to disk as '{local_config_filename}'")
    
    commit_file_to_github(repo, local_config_filename, yaml.dump(derived_yaml_config, default_flow_style=False, sort_keys=False), branch=inputs['default_branch'])

    # Step 8: Modular Template Injection Loop
    print("\n[8/8] Generating and Injecting Decentralized Modular Workflow Templates...")
    commit_file_to_github(repo, ".github/workflows/pr-gate.yml", generate_dynamic_pr_gate_yml(inputs), branch=inputs['default_branch'])
    commit_file_to_github(repo, ".github/workflows/snowflake-delivery-master.yml", generate_dynamic_master_delivery_yml(inputs), branch=inputs['default_branch'])
    
    for b_name in inputs['branch_sequence']:
        b_inputs = inputs['branch_data'][b_name]
        if b_inputs['has_snowflake']:
            commit_file_to_github(repo, f".github/workflows/snowflake-pipeline-{b_name}.yml", generate_dynamic_branch_pipeline_yml(b_name, b_inputs, inputs), branch=inputs['default_branch'])
        if b_inputs['has_email_gate']:
            commit_file_to_github(repo, f".github/workflows/business-email-gate-{b_name}.yml", generate_dynamic_business_gate_yml(b_name, b_inputs, inputs), branch=inputs['default_branch'])

    print(f"\n{'='*60}")
    print(" UNIFIED PIPELINE MATRIX GENERATED AND DEPLOYED SUCCESSFULLY!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
