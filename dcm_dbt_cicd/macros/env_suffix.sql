{% macro env_suffix() %}
    {% if target.name == 'prod' %}
        _PROD
    {% else %}
        _DEV
    {% endif %}
{% endmacro %}