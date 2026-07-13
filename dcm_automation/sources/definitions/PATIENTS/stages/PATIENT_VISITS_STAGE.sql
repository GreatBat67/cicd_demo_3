DEFINE STAGE {{ database }}.PATIENTS.PATIENT_VISITS_STAGE
DIRECTORY = ( ENABLE = TRUE )
COMMENT = 'Internal stage for incoming patient visit files (CSV)'