-- ====================================================
-- CREATE DCM PROJECTS
-- ====================================================

-- ----------------------------------------------------
-- Environment : DEV
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_DEMO_DEV;
USE SCHEMA CICD_DEMO_DEV.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_DEMO_DEV.UTILITIES.DCM_demo
COMMENT = 'DCM Project - DEV';

-- ----------------------------------------------------
-- Environment : QA
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_DEMO_QA;
USE SCHEMA CICD_DEMO_QA.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_DEMO_QA.UTILITIES.DCM_demo
COMMENT = 'DCM Project - QA';

-- ----------------------------------------------------
-- Environment : PROD
-- ----------------------------------------------------
USE ROLE PSEUDO_ACCOUNTADMIN;
USE DATABASE CICD_DEMO_PROD;
USE SCHEMA CICD_DEMO_PROD.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_DEMO_PROD.UTILITIES.DCM_demo
COMMENT = 'DCM Project - PROD';
