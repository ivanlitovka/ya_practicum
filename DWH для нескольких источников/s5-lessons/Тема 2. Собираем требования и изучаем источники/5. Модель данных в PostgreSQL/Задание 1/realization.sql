SELECT DISTINCT (event_value::json #>> '{product_payments,0,product_name}') AS prod
FROM outbox o
WHERE (event_value::json #>> '{product_payments,0,product_name}') IS NOT NULL;