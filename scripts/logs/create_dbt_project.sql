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
COMMENT = 'DBT Project - DEV';

GRANT OWNERSHIP ON DBT PROJECT CICD_AUTOMATION_DEV.UTILITIES.dcm_dbt_cicd TO ROLE GITHUB_CICD_DEMO_ROLE COPY CURRENT GRANTS ;

-- ----------------------------------------------------
-- Environment : QA
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_QA;
USE SCHEMA CICD_AUTOMATION_QA.UTILITIES;

CREATE DBT PROJECT IF NOT EXISTS CICD_AUTOMATION_QA.UTILITIES.dcm_dbt_cicd
COMMENT = 'DBT Project - QA';

GRANT OWNERSHIP ON DBT PROJECT CICD_AUTOMATION_QA.UTILITIES.dcm_dbt_cicd TO ROLE GITHUB_CICD_DEMO_ROLE COPY CURRENT GRANTS ;

-- ----------------------------------------------------
-- Environment : PROD
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_PROD;
USE SCHEMA CICD_AUTOMATION_PROD.UTILITIES;

CREATE DBT PROJECT IF NOT EXISTS CICD_AUTOMATION_PROD.UTILITIES.dcm_dbt_cicd
COMMENT = 'DBT Project - PROD';

GRANT OWNERSHIP ON DBT PROJECT CICD_AUTOMATION_PROD.UTILITIES.dcm_dbt_cicd TO ROLE GITHUB_CICD_DEMO_ROLE COPY CURRENT GRANTS ;
