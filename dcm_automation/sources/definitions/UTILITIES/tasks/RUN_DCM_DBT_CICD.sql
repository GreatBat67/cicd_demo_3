DEFINE TASK {{ database }}.UTILITIES.RUN_DCM_DBT_CICD
	warehouse=DISHA_RANI_WH
	schedule='USING CRON 0 0 */2 * * UTC'
	as EXECUTE DBT PROJECT {{ database }}.UTILITIES.DCM_DBT_CICD
    ARGS = 'run';