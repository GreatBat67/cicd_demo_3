DEFINE DBT PROJECT CICD_AUTOMATION{{env_suffix}}.utilities.DCM_DBT_CICD
    FROM 'sources/dbt/dcm_dbt_cicd'
    DEFAULT_TARGET = 'DCM_DEV' 
;