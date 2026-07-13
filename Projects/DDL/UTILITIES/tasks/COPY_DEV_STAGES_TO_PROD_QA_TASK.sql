create or replace task COPY_DEV_STAGES_TO_PROD_QA_TASK
	warehouse=DISHA_RANI_WH
	schedule='USING CRON 00 12 * * * Asia/Kolkata'
	as CALL CICD_AUTOMATION{{env_suffix}}.UTILITIES.COPY_DEV_STAGES_TO_PROD_QA();