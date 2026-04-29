CREATE SCHEMA IF NOT EXISTS prod;

CREATE TABLE IF NOT EXISTS prod.customer_research AS
SELECT
    cr.date_id,
    cr.geo_id,
    cr.sales_qty,
    cr.sales_amt
FROM
    stage.customer_research AS cr;

CREATE TABLE IF NOT EXISTS prod.user_activity_log AS
SELECT
    ual.date_time,
    ual.customer_id
FROM
    stage.user_activity_log AS ual;

CREATE TABLE IF NOT EXISTS prod.user_order_log AS
SELECT
    uol.date_time,
    uol.customer_id,
    uol.quantity,
    uol.payment_amount
FROM
    stage.user_order_log AS uol;