-- ====================================================
-- CREATE DCM PROJECTS
-- ====================================================

-- ----------------------------------------------------
-- Environment : DEV
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_DEV;
USE SCHEMA CICD_AUTOMATION_DEV.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_AUTOMATION_DEV.UTILITIES.DCM_AUTOMATION
COMMENT = 'DCM Project - DEV';

-- ----------------------------------------------------
-- Environment : QA
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_QA;
USE SCHEMA CICD_AUTOMATION_QA.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_AUTOMATION_QA.UTILITIES.DCM_AUTOMATION
COMMENT = 'DCM Project - QA';

-- ----------------------------------------------------
-- Environment : PROD
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_AUTOMATION_PROD;
USE SCHEMA CICD_AUTOMATION_PROD.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_AUTOMATION_PROD.UTILITIES.DCM_AUTOMATION
COMMENT = 'DCM Project - PROD';
