-- ============================================================
-- DEV
-- ============================================================

USE ROLE GITHUB_CICD_DEMO_ROLE;
USE DATABASE CICD_demo_AUTOMATION_DEV;
USE SCHEMA CICD_demo_AUTOMATION_DEV.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_demo_AUTOMATION_DEV.UTILITIES.DCM_AUTOMATION_demo
COMMENT = 'DCM Project - DEV';

-- ============================================================
-- QA
-- ============================================================

USE ROLE GITHUB_CICD_DEMO_ROLE;
USE DATABASE CICD_demo_AUTOMATION_QA;
USE SCHEMA CICD_demo_AUTOMATION_QA.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_demo_AUTOMATION_QA.UTILITIES.DCM_AUTOMATION_demo
COMMENT = 'DCM Project - QA';

-- ============================================================
-- PROD
-- ============================================================

USE ROLE GITHUB_CICD_DEMO_ROLE;
USE DATABASE CICD_demo_AUTOMATION_PROD;
USE SCHEMA CICD_demo_AUTOMATION_PROD.UTILITIES;

CREATE DCM PROJECT IF NOT EXISTS CICD_demo_AUTOMATION_PROD.UTILITIES.DCM_AUTOMATION_demo
COMMENT = 'DCM Project - PROD';