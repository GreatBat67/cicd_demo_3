name: "Snowflake Script Orchestration Matrix"

on:
  push:
    branches:
      - dev
      - qa
      - cicd
      - main
    paths:
      - "db_schema/**"
      - "config/**"
      - "dcm/**"
      - "scripts/**"
  workflow_dispatch:
permissions:
  id-token: write
  contents: read

jobs:
  execute-orchestrator:
    runs-on: ubuntu-latest
    
    # Resolves promotion tiering dynamically based on execution branch name
    environment: ${{ github.ref_name == 'main' && 'main' || github.ref_name }}
    
    steps:
      - name: "Checkout Repository Codebase"
        uses: actions/checkout@v4

      - name: "Set up Enterprise Python Environment"
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: "./requirements.txt" 
      - name: "Install Core Python Dependencies"
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: "Initialize Snowflake CLI Context Interface"
        uses: snowflakedb/snowflake-cli-action@v2.0
        with:
          use-oidc: true

      - name: "Execute Custom Python Automation Orchestrator Pipeline"
        env:
          SNOWFLAKE_ACCOUNT: "${{ vars.SNOWFLAKE_ACCOUNT }}"
          SNOWFLAKE_ROLE: "${{ vars.SNOWFLAKE_ROLE }}"
          SNOWFLAKE_USER: "${{ vars.SNOWFLAKE_USER }}"
          SNOWFLAKE_WAREHOUSE: "${{ vars.SNOWFLAKE_WAREHOUSE }}"
          SNOWFLAKE_DATABASE: "${{ vars.SNOWFLAKE_DATABASES }}"
          SNOWFLAKE_SCHEMA: "${{ vars.SNOWFLAKE_SCHEMAS }}"
        run: |
          echo "🚀 Initializing Orchestrator Pipeline Run for Tier: [${{ github.ref_name }}]"
          python scripts/initialise_project.py --stop-on-error
