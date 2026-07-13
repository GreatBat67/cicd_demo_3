{{ config(
    materialized='incremental',
    unique_key='patient_id'
) }}

with source_data as (

    select *
    from {{ source('bronze', 'patients') }}

),

patients as (

    select
        patient_id,
        upper(full_name) as full_name,
        try_to_date(date_of_birth) as date_of_birth,
        gender,
        phone_number,
        city
    from source_data

)

select * from patients

{% if is_incremental() %}

-- only process new/updated records
where patient_id not in (select patient_id from {{ this }})

{% endif %}