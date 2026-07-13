create or replace task RUN_DCM_DBT_CICD
	warehouse=DISHA_RANI_WH
	schedule='USING CRON 0 0 */2 * * UTC'
	as EXECUTE DBT PROJECT CICD_AUTOMATION{{env_suffix}}.UTILITIES.DCM_DBT_CICD
    ARGS = 'run';