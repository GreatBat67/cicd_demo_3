DEFINE STAGE {{ database }}.PATIENTS.PATIENTS_STAGE
DIRECTORY = ( ENABLE = TRUE )
COMMENT = 'Internal stage for incoming patient  files (CSV)'