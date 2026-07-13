# Setup generalized, parameterized template architecture managing Snowflake pipelines modularly
"""
Usage (Automated Template Generation):
    python consolidates.py --input-file pipeline_inputs_v2.yaml

Requirements:
    pip install PyGithub PyYAML requests pynacl
"""

import argparse
import os
import sys
import yaml
import requests
import github
from github import Github, GithubException


def compile_yaml_config_structure(inputs):
    """Assembles an adaptive dictionary layout matching the user's custom branch list."""
    config = {
        "repo_name": inputs['repo_name'],
        "owner": inputs['owner'],
        "project_name": inputs['project_name'],
        "default_branch": inputs['branch_sequence'][0],
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
            config["final_branch"] = b
            b_cfg["locked"] = True
            b_cfg["protection"]["lock_branch"] = True
            b_cfg["protection"]["restrict_pushes"] = True
            
        config["branches"][b] = b_cfg
        
    return config


# ==========================================================
# 📋 DECOUPLED TEMPLATE WORKFLOW GENERATORS (EMOJI-FREE)
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
    """Builds a centralized entry router managing custom paths and routing to the single core engine."""
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
        if not b_inputs['has_snowflake']:
            continue
            
        if b_inputs['has_email_gate']:
            workflow += f"""
  {b}-business-approval-gate:
    if: github.base_ref == '{b}' && github.event_name == 'pull_request'
    uses: ./.github/workflows/business-email-gate-{b}.yml
    secrets: inherit"""
            
        if b_inputs['has_email_gate']:
            condition_str = f"github.ref_name == '{b}' && github.event_name == 'push'"
        else:
            condition_str = f"(github.base_ref == '{b}' && github.event_name == 'pull_request') || (github.ref_name == '{b}' && github.event_name == 'push')"
            
        workflow += f"""
  {b}-parameterized-pipeline:
    if: {condition_str}"""
        if b_inputs['has_email_gate']:
            workflow += f"\n    needs: {b}-business-approval-gate"
            
        workflow += f"""
    uses: ./.github/workflows/snowflake-pipeline-engine.yml
    with:
      environment_tier: "{b}"
      target_database: "{b_inputs['sf_db']}"
      target_schema: "{b_inputs['sf_schema']}"
      dcm_target_flag: "{b_inputs['dcm_target']}"
      execute_phase: "${{{{ github.event_name == 'pull_request' && 'plan' || 'deploy' }}}}"
    secrets: inherit"""
            
    return workflow


def generate_parameterized_engine_yml(inputs):
    """Generates the Single Reusable Engine Workflow that abstracts away specific environments."""
    return f"""name: "Snowflake Core: Parameterized Execution Engine"
on:
  workflow_call:
    inputs:
      environment_tier:
        required: true
        type: string
      target_database:
        required: true
        type: string
      target_schema:
        required: true
        type: string
      dcm_target_flag:
        required: true
        type: string
      execute_phase:
        required: true
        type: string

env:
  SNOWFLAKE_ACCOUNT: "{inputs['sf_account']}"
  SNOWFLAKE_ROLE: "{inputs['sf_role']}"
  SNOWFLAKE_WAREHOUSE: "{inputs['sf_warehouse']}"
  SNOWFLAKE_CLI_FEATURES_ENABLE_SNOWFLAKE_PROJECTS: "true"
  SNOWFLAKE_DATABASE: "${{{{ inputs.target_database }}}}"
  SNOWFLAKE_SCHEMA: "${{{{ inputs.target_schema }}}}"

jobs:
  orchestrate-lifecycle:
    runs-on: ubuntu-latest
    environment: "${{{{ inputs.environment_tier }}}}"
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Snowflake CLI Connection
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true

      - name: Invoke Modular DCM Processing Step
        uses: ./.github/workflows/modules/action-dcm-engine
        with:
          execute_phase: "${{{{ inputs.execute_phase }}}}"
          dcm_target_flag: "${{{{ inputs.dcm_target_flag }}}}"

      - name: Invoke Modular dbt Compilation Step
        uses: ./.github/workflows/modules/action-dbt-engine
        with:
          execute_phase: "${{{{ inputs.execute_phase }}}}"
          dcm_target_flag: "${{{{ inputs.dcm_target_flag }}}}"
"""


def generate_module_dcm_yml():
    """Generates the independent execution step module for Data Cloud Manager actions."""
    return """name: "Module Step: DCM Processor"
description: "Handles isolated pipeline execution loops for Snowflake Data Cloud Manager actions"
inputs:
  execute_phase:
    required: true
  dcm_target_flag:
    required: true

runs:
  using: "composite"
  steps:
    - name: Run DCM Plan Phase
      if: inputs.execute_phase == 'plan'
      shell: bash
      run: |
        echo "Running DCM infrastructure validation mapping..."
        cd dcm_automation
        snow dcm plan --target ${{ inputs.dcm_target_flag }} -x

    - name: Run DCM Live Deploy Phase
      if: inputs.execute_phase == 'deploy'
      shell: bash
      run: |
        echo "LIVE: Processing automated DCM infrastructure deployment..."
        cd dcm_automation
        snow dcm deploy --target ${{ inputs.dcm_target_flag }} -x
"""


def generate_module_dbt_yml():
    """Generates the independent execution step module for dbt lifecycle triggers."""
    return """name: "Module Step: dbt Transformer"
description: "Handles isolated pipeline execution loops for composite dbt model compilation"
inputs:
  execute_phase:
    required: true
  dcm_target_flag:
    required: true

runs:
  using: "composite"
  steps:
    - name: Compile and Deploy Local dbt Sandbox Environments
      if: inputs.execute_phase == 'plan'
      shell: bash
      run: |
        echo "Building test environment for dbt transformations..."
        snow dbt deploy dbt_project_dev --source ./dcm_dbt_cicd --force -x

    - name: Live Execution of Production Grade dbt Transformations
      if: inputs.execute_phase == 'deploy'
      shell: bash
      run: |
        echo "LIVE: Synchronizing and running targeted dbt project models..."
        snow dbt deploy dbt_project_prod --source ./dcm_dbt_cicd --force -x
        snow dbt execute -x dbt_project_prod run --target ${{ inputs.dcm_target_flag }}
"""


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
                    content=f"# {repo.name}\nScaffolded Dynamic Gated Architecture Template.",
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
    g = Github(auth=github.Auth.Token(token))
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
    parser = argparse.ArgumentParser(description="Autonomous Gated Architecture Orchestration Engine")
    parser.add_argument("--input-file", help="Path to pre-built YAML configuration input parameter file")
    args = parser.parse_args()

    token = "ghp_..."

    if not token or token.strip() == "":
        print("CRITICAL EXCEPTION: Token variable is completely empty inside the execution script.")
        sys.exit(1)

    target_file = args.input_file if args.input_file else "pipeline_inputs_v2.yaml"
    
    if not os.path.exists(target_file):
        print(f"Error: Specified template matrix configuration path '{target_file}' does not exist.")
        sys.exit(1)
        
    print(f"Parsing configuration from: '{target_file}'...")
    with open(target_file, "r") as f:
        inputs = yaml.safe_load(f)
        
    inputs['default_branch'] = inputs['branch_sequence'][0]
    derived_yaml_config = compile_yaml_config_structure(inputs)
    
    # Authenticate cleanly with current API models to eliminate token warnings
    auth = github.Auth.Token(token)
    g = Github(auth=auth)
    full_repo_path = f"{inputs['owner']}/{inputs['repo_name']}"
    
    try:
        repo = g.get_repo(full_repo_path)
    except GithubException as e:
        if e.status == 404:
            print(f"\nRepository '{full_repo_path}' was not found.")
            print("Automatically provisioning missing target repository structure...")
            repo = create_new_github_repository(g, inputs['owner'], inputs['repo_name'], inputs['project_name'])
        else:
            print(f"Access denied or unhandled GitHub connection error: {e}")
            sys.exit(1)

    print("\n" + "="*60)
    print("   STARTING MODULAR TEMPLATE INJECTION MATRIX")
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
            repo.create_secret("BUSINESS_GATE_IMAP_PASSWORD", inputs.get('imap_pass', ''))
            print("  [SECRET ENCRYPTED] 'BUSINESS_GATE_IMAP_PASSWORD' successfully added.")
        except Exception as err:
            print(f"  [WARNING] Failed to run cryptographic secrets generation: {err}")
    else:
        print("\n[6/8] Skipping Secret Provisioning (No email authorization gate requested).")

    # Step 7: Spec Sheet Local Archive
    print("\n[7/8] Archiving Automated Config Specs...")
    local_config_filename = "github_gates_config.yaml"
    commit_file_to_github(repo, local_config_filename, yaml.dump(derived_yaml_config, default_flow_style=False, sort_keys=False), branch=inputs['default_branch'])

    # Step 8: Modular Template Injection Loop
    print("\n[8/8] Generating and Injecting Decentralized Modular Workflow Templates...")
    
    # Core Gate and Master Router
    commit_file_to_github(repo, ".github/workflows/pr-gate.yml", generate_dynamic_pr_gate_yml(inputs), branch=inputs['default_branch'])
    commit_file_to_github(repo, ".github/workflows/snowflake-delivery-master.yml", generate_dynamic_master_delivery_yml(inputs), branch=inputs['default_branch'])
    
    # Unified core parameterized engine (Single source of truth)
    commit_file_to_github(repo, ".github/workflows/snowflake-pipeline-engine.yml", generate_parameterized_engine_yml(inputs), branch=inputs['default_branch'])
    
    # Standalone step modules (Decoupled layout)
    commit_file_to_github(repo, ".github/workflows/modules/action-dcm-engine/action.yml", generate_module_dcm_yml(), branch=inputs['default_branch'])
    commit_file_to_github(repo, ".github/workflows/modules/action-dbt-engine/action.yml", generate_module_dbt_yml(), branch=inputs['default_branch'])
    
    for b_name in inputs['branch_sequence']:
        b_inputs = inputs['branch_data'][b_name]
        if b_inputs['has_email_gate']:
            commit_file_to_github(repo, f".github/workflows/business-email-gate-{b_name}.yml", generate_dynamic_business_gate_yml(b_name, b_inputs, inputs), branch=inputs['default_branch'])

    print(f"\n{'='*60}")
    print(" TEMPLATE PIPELINE MATRIX GENERATED AND DEPLOYED SUCCESSFULLY!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()