-- Call grants macro to create standard roles for the database


    DEFINE ROLE CICD_PROD_DEVELOPER_PROD;
    DEFINE ROLE CICD_PROD_READONLY_PROD;

-- ======================================================
-- OWNER ROLE GRANTS
-- ======================================================

grant usage on database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant usage on all schemas in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant usage on future schemas in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


-- =========================
-- TABLES
-- =========================

grant select, insert, update, delete, truncate 
on all tables in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant select, insert, update, delete, truncate 
on future tables in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



-- =========================
-- VIEWS
-- =========================

grant select, references
on all views in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant select, references
on future views in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



-- =========================
-- DYNAMIC TABLES
-- =========================

grant select, monitor, operate
on all dynamic tables in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant select, monitor, operate
on future dynamic tables in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



-- =========================
-- STAGES
-- =========================

grant read 
on all stages in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant read 
on future stages in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant write 
on all stages in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant write 
on future stages in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



-- =========================
-- TASKS
-- =========================

grant operate 
on all tasks in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;


grant operate 
on future tasks in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



-- =========================
-- CREATE PRIVILEGES
-- =========================

grant create schema 
on database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



grant create table,
      create view,
      create dynamic table,
      create stage,
      create task,
      create stream,
      create file format
on all schemas in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



grant create dynamic table,
      create task,
      create stage
on future schemas in database CICD_DEMO_PROD
    to role GITHUB_CICD_DEMO_ROLE;



    -- =========================
    -- DEVELOPER ACCESS (FULL CONTROL)
    -- =========================

    grant usage on database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant usage on all schemas in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant usage on future schemas in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, insert, update, delete, truncate on all tables in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, insert, update, delete, truncate on future tables in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, references on all views in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, references on future views in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, monitor, operate on all dynamic tables in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant select, monitor, operate on future dynamic tables in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant read on all stages in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant read on future stages in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant write on all stages in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant write on future stages in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant operate on all tasks in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant operate on future tasks in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant create schema on database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant create table,
          create view,
          create dynamic table,
          create stage,
          create task,
          create stream,
          create file format
        on all schemas in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant create dynamic table,
          create task,
          create stage
        on future schemas in database CICD_DEMO_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    -- =========================
    -- ROLE HIERARCHY
    -- =========================
    grant role CICD_PROD_READONLY_PROD
        to role CICD_PROD_DEVELOPER_PROD;

    grant role CICD_PROD_DEVELOPER_PROD
        to role GITHUB_CICD_DEMO_ROLE;

    -- =========================
    -- READONLY ACCESS
    -- =========================

    grant usage on database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant usage on all schemas in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant usage on future schemas in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on all tables in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on future tables in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on all views in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on future views in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on all dynamic tables in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant select on future dynamic tables in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant read on all stages in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

    grant read on future stages in database CICD_DEMO_PROD
        to role CICD_PROD_READONLY_PROD;

