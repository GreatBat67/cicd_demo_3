-- internal stage

DEFINE STAGE CICD_DEMO_DEV.PROJECTS.PATIENTS_STAGE
    DIRECTORY = ( ENABLE = TRUE )
    COMMENT = 'Internal stage for incoming patient files (CSV)'
;
