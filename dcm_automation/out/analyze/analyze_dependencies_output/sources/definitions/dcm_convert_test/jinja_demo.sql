-- Call grants macro to create standard roles for the database


-- ======================================================
-- CREATE SCHEMA
-- ======================================================

CREATE SCHEMA IF NOT EXISTS PROJECTS.DCM_DEV;

-- ======================================================
-- SCHEMA OWNERSHIP (for new objects)
-- ======================================================

GRANT OWNERSHIP ON SCHEMA PROJECTS.DCM_DEV
TO ROLE GITHUB_CICD_DEMO_ROLE
COPY CURRENT GRANTS;

-- ======================================================
-- EXISTING TABLE OWNERSHIP (fix MODIFY / access issues)
-- ======================================================

GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJECTS.DCM_DEV
TO ROLE GITHUB_CICD_DEMO_ROLE
COPY CURRENT GRANTS;

-- ======================================================
-- FUTURE OBJECT DEFAULT PRIVILEGES
-- ======================================================

ALTER DEFAULT PRIVILEGES IN SCHEMA PROJECTS.DCM_DEV
GRANT ALL ON TABLES TO ROLE GITHUB_CICD_DEMO_ROLE;

-- ======================================================
-- DATABASE ACCESS
-- ======================================================

GRANT USAGE ON DATABASE PROJECTS
TO ROLE GITHUB_CICD_DEMO_ROLE;

-- ======================================================
-- OPTIONAL: OBJECT CREATION PRIVILEGES
-- ======================================================

GRANT CREATE TABLE,
      CREATE VIEW,
      CREATE STAGE,
      CREATE TASK,
      CREATE FILE FORMAT,
      CREATE STREAM,
      CREATE DYNAMIC TABLE
ON SCHEMA PROJECTS.DCM_DEV
TO ROLE GITHUB_CICD_DEMO_ROLE;

