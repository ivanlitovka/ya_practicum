

create table if NOT exists stage.customer_research (
    id int primary key not null,
    date_id TIMESTAMP,
    category_id int,
    geo_id int,
    sales_qty int,
    sales_amt numeric(14,2)
);


create table if not exists stage.user_activity_log (
    id integer primary key not null,
    date_time timestamp,
    action_id bigint,
    customer_id bigint,
    quantity bigint
);

create table if not exists stage.user_order_log (
    id int primary key,
    date_time timestamp,
    city_id int,
    city_name varchar(100),
    customer_id bigint,
    first_name varchar(100),
    last_name varchar(100),
    item_id int,
    item_name varchar(100),
    quantity bigint,
    payment_amount numeric(14,2)
)