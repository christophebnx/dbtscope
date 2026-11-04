{% snapshot products_snapshot %}
{{ config(target_schema='snapshots', unique_key='product_id', strategy='check', check_cols='all') }}
select * from {{ ref('stg_erp__products') }}
{% endsnapshot %}
