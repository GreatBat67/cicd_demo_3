{% macro create_dcm_project(database, schemas, roles, project_owner_role) %}

-- Grants for role: GITHUB_CICD_DEMO_ROLE

GRANT USAGE ON DATABASE {{ database }} TO ROLE GITHUB_CICD_DEMO_ROLE;

{% for schema in schemas %}
{% set full_schema = database ~ '.' ~ schema %}

GRANT USAGE ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;

GRANT CREATE DBT PROJECT ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE DCM PROJECT ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE DYNAMIC TABLE ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE FILE FORMAT ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE FUNCTION ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE PROCEDURE ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE STAGE ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE STREAM ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE TABLE ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE TASK ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT CREATE VIEW ON SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;

GRANT SELECT ON ALL TABLES IN SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA {{ full_schema }} TO ROLE GITHUB_CICD_DEMO_ROLE;

{% endfor %}

{% if roles|length > 1 %}
{% for i in range(roles|length - 1) %}
GRANT ROLE {{ roles[i] }} TO ROLE {{ roles[i + 1] }};
{% endfor %}
{% if roles[-1] != project_owner_role %}
GRANT ROLE {{ roles[-1] }} TO ROLE {{ project_owner_role }};
{% endif %}
{% endif %}

{% endmacro %}