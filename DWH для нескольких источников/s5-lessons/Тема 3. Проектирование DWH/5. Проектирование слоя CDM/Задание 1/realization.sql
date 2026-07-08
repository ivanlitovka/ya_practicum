drop table if exists cdm.dm_settlement_report;
create table if not exists cdm.dm_settlement_report(
    id serial primary key not null,
    restaurant_id varchar(255) not null,
    restaurant_name varchar(255) not null,
    settlement_date date not null,
    orders_count int not null,
    orders_total_sum numeric(14,2) not NULL,
    orders_bonus_payment_sum numeric(14,2) NOT NULL,
    orders_bonus_granted_sum numeric(14,2) NOT NULL,
    order_processing_fee numeric(14,2) NOT NULL,
    restaurant_reward_sum numeric(14,2) NOT NULL
);