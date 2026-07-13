DEFINE STAGE {{ database }}.HOSPITALS.HOSPITALS_STAGE
DIRECTORY = ( ENABLE = TRUE )
COMMENT = 'Internal stage for incoming patient  files (CSV)'