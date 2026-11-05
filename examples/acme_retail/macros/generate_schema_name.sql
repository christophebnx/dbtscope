{#- The custom schema as is (`sales`, not `main_sales`); the target schema when none is set. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ custom_schema_name | trim if custom_schema_name is not none else target.schema }}
{%- endmacro %}
