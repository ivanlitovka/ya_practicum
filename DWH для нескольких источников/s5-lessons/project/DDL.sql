-- STG для курьеров (из API /couriers)
CREATE TABLE IF NOT EXISTS stg.couriers (
    id SERIAL PRIMARY KEY,
    courier_id VARCHAR NOT NULL UNIQUE,
    courier_name VARCHAR NOT NULL,
    load_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- STG для доставок (из API /deliveries)
CREATE TABLE IF NOT EXISTS stg.deliveries (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    order_ts TIMESTAMP,
    delivery_id VARCHAR NOT NULL UNIQUE,
    courier_id VARCHAR NOT NULL,
    address TEXT,
    delivery_ts TIMESTAMP,
    rate INT CHECK (rate BETWEEN 1 AND 5),
    sum NUMERIC(19,5),
    tip_sum NUMERIC(19,5),
    load_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Измерение "Курьеры"
CREATE TABLE IF NOT EXISTS dds.dm_couriers (
    id SERIAL PRIMARY KEY,
    courier_id VARCHAR NOT NULL UNIQUE,
    courier_name VARCHAR NOT NULL
);

ALTER TABLE dds.dm_orders ADD COLUMN IF NOT EXISTS courier_id INT REFERENCES dds.dm_couriers(id);

-- Факт "Доставки"
CREATE TABLE IF NOT EXISTS dds.fct_deliveries (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES dds.dm_orders(id),
    courier_id INT NOT NULL REFERENCES dds.dm_couriers(id),
    delivery_ts TIMESTAMP NOT NULL,
    rate INT NOT NULL CHECK (rate BETWEEN 1 AND 5),
    tip_sum NUMERIC(19,5) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, courier_id)
);

-- Витрина курьеров

CREATE TABLE IF NOT EXISTS cdm.dm_courier_ledger (
    id SERIAL PRIMARY KEY,
    courier_id VARCHAR NOT NULL,
    courier_name VARCHAR NOT NULL,
    settlement_year INT NOT NULL,
    settlement_month INT NOT NULL CHECK (settlement_month BETWEEN 1 AND 12),
    orders_count INT NOT NULL DEFAULT 0,
    orders_total_sum NUMERIC(19,5) NOT NULL DEFAULT 0,
    rate_avg NUMERIC(3,2) NOT NULL DEFAULT 0,
    order_processing_fee NUMERIC(19,5) NOT NULL DEFAULT 0,
    courier_order_sum NUMERIC(19,5) NOT NULL DEFAULT 0,
    courier_tips_sum NUMERIC(19,5) NOT NULL DEFAULT 0,
    courier_reward_sum NUMERIC(19,5) NOT NULL DEFAULT 0,
    UNIQUE(courier_id, settlement_year, settlement_month)
);