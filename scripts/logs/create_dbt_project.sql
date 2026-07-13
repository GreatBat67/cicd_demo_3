-- ====================================================
-- CREATE DBT PROJECTS
-- ====================================================

-- ----------------------------------------------------
-- Environment : DEV
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_DEV;
USE SCHEMA CICD_AUTOMATION_DEV.UTILITIES;

CREATE DBT PROJECT IF NOT EXISTS CICD_AUTOMATION_DEV.UTILITIES.dcm_dbt_cicd
FROM 'snow://workspace/USER$DISHA_RANI.PUBLIC.CI_CD_STANDARD_TIER_OFFERING_TEMPLATE/versions/live/dcm_dbt_cicd/'
DEFAULT_TARGET = 'DCM_DEV'
EXTERNAL_ACCESS_INTEGRATIONS = ()
COMMENT = 'DBT Project - DEV';

-- ----------------------------------------------------
-- Environment : QA
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_QA;
USE SCHEMA CICD_AUTOMATION_QA.UTILITIES;

CREATE DBT PROJECT IF NOT EXISTS CICD_AUTOMATION_QA.UTILITIES.dcm_dbt_cicd
FROM 'snow://workspace/USER$DISHA_RANI.PUBLIC.CI_CD_STANDARD_TIER_OFFERING_TEMPLATE/versions/live/dcm_dbt_cicd/'
DEFAULT_TARGET = 'DCM_QA'
EXTERNAL_ACCESS_INTEGRATIONS = ()
COMMENT = 'DBT Project - QA';

-- ----------------------------------------------------
-- Environment : PROD
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_PROD;
USE SCHEMA CICD_AUTOMATION_PROD.UTILITIES;

CREATE DBT PROJECT IF NOT EXISTS CICD_AUTOMATION_PROD.UTILITIES.dcm_dbt_cicd
FROM 'snow://workspace/USER$DISHA_RANI.PUBLIC.CI_CD_STANDARD_TIER_OFFERING_TEMPLATE/versions/live/dcm_dbt_cicd/'
DEFAULT_TARGET = 'DCM_PROD'
EXTERNAL_ACCESS_INTEGRATIONS = ()
COMMENT = 'DBT Project - PROD';
