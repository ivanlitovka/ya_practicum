CREATE TABLE IF NOT EXISTS stage.customer_research (
    id serial PRIMARY KEY NOT NULL,
    date_id TIMESTAMP,
    category_id int,
    geo_id int,
    sales_qty int,
    sales_amt numeric(14, 2)
);

CREATE TABLE IF NOT EXISTS stage.user_activity_log (
    id serial PRIMARY KEY NOT NULL,
    date_time timestamp,
    action_id bigint,
    customer_id bigint,
    quantity bigint
);

CREATE TABLE IF NOT EXISTS stage.user_order_log (
    id serial PRIMARY KEY,
    date_time timestamp,
    city_id int,
    city_name varchar(100),
    customer_id bigint,
    first_name varchar(100),
    last_name varchar(100),
    item_id int,
    item_name varchar(100),
    quantity bigint,
    payment_amount numeric(14, 2)
)