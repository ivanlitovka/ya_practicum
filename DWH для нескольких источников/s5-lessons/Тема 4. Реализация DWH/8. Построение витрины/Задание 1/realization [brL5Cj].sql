
drop table if exists cdm.dm_settlement_report;


CREATE TABLE cdm.dm_settlement_report (
id serial not null,
restaurant_id varchar not null,
restaurant_name varchar not null,
settlement_date date not null,
orders_count integer not null,
orders_total_sum numeric(14, 2) not null,
orders_bonus_payment_sum numeric(14, 2) not null,
orders_bonus_granted_sum numeric(14, 2) not null,
order_processing_fee numeric(14, 2) not null,
restaurant_reward_sum numeric(14, 2) not null
);

ALTER TABLE cdm.dm_settlement_report ADD PRIMARY KEY (id);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_settlement_date_check CHECK (settlement_date >= '2022-01-01' AND settlement_date < '2500-01-01');
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN orders_count SET DEFAULT 0;
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN orders_total_sum SET DEFAULT 0;
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN orders_bonus_payment_sum SET DEFAULT 0;
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN orders_bonus_granted_sum SET DEFAULT 0;
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN order_processing_fee SET DEFAULT 0;
ALTER TABLE cdm.dm_settlement_report ALTER COLUMN restaurant_reward_sum SET DEFAULT 0;

ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_orders_count_check CHECK (orders_count >= 0);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_orders_total_sum_check CHECK (orders_total_sum >= 0);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_orders_bonus_payment_sum_check CHECK (orders_bonus_payment_sum >= 0);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_orders_bonus_granted_sum_check CHECK (orders_bonus_granted_sum >= 0);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_order_processing_fee_check CHECK (order_processing_fee >= 0);
ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_restaurant_reward_sum_check CHECK (restaurant_reward_sum >= 0);


ALTER TABLE cdm.dm_settlement_report ADD CONSTRAINT dm_settlement_report_restaurant_id_settlement_date UNIQUE (restaurant_id, settlement_date);






;WITH order_sums AS (
    SELECT
        r.id                      AS restaurant_id,
        r.restaurant_name         AS restaurant_name,
        tss.date                  AS settlement_date,
        COUNT(DISTINCT orders.id) AS orders_count,
        SUM(fct.total_sum)        AS orders_total_sum,
        SUM(fct.bonus_payment)    AS orders_bonus_payment_sum,
        SUM(fct.bonus_grant)      AS orders_bonus_granted_sum
    FROM dds.fct_product_sales as fct
        INNER JOIN dds.dm_orders AS orders
            ON fct.order_id = orders.id
        INNER JOIN dds.dm_timestamps as tss
            ON tss.id = orders.timestamp_id
        INNER JOIN dds.dm_restaurants AS r
            on r.id = orders.restaurant_id
    WHERE orders.order_status = 'CLOSED'
    GROUP BY
        r.id,
        r.restaurant_name,
        tss.date
)
INSERT INTO cdm.dm_settlement_report(
    restaurant_id,
    restaurant_name,
    settlement_date,
    orders_count,
    orders_total_sum,
    orders_bonus_payment_sum,
    orders_bonus_granted_sum,
    order_processing_fee,
    restaurant_reward_sum
)
SELECT
    restaurant_id,
    restaurant_name,
    settlement_date,
    orders_count,
    orders_total_sum,
    orders_bonus_payment_sum,
    orders_bonus_granted_sum,
    s.orders_total_sum * 0.25 AS order_processing_fee,
    s.orders_total_sum - s.orders_total_sum * 0.25 - s.orders_bonus_payment_sum AS restaurant_reward_sum
FROM order_sums AS s
ON CONFLICT (restaurant_id, settlement_date) DO UPDATE
SET
    orders_count = EXCLUDED.orders_count,
    orders_total_sum = EXCLUDED.orders_total_sum,
    orders_bonus_payment_sum = EXCLUDED.orders_bonus_payment_sum,
    orders_bonus_granted_sum = EXCLUDED.orders_bonus_granted_sum,
    order_processing_fee = EXCLUDED.order_processing_fee,
    restaurant_reward_sum = EXCLUDED.restaurant_reward_sum;