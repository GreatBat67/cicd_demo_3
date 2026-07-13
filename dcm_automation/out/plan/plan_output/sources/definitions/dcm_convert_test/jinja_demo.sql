-- Call grants macro to create standard roles for the database



-- ======================================================
-- EXISTING TABLE OWNERSHIP (fix MODIFY / access issues)
-- ======================================================

GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJECTS.DCM_DEV
TO ROLE GITHUB_CICD_DEMO_ROLE
COPY CURRENT GRANTS;


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

