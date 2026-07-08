-- ordersystem_orders (из коллекции orders)
DROP TABLE IF EXISTS stg.ordersystem_orders;
CREATE TABLE stg.ordersystem_orders (
    id serial PRIMARY KEY,
    object_id varchar NOT NULL,
    object_value text NOT NULL,
    update_ts timestamp NOT NULL
);

-- ordersystem_restaurants (из коллекции restaurants)
DROP TABLE IF EXISTS stg.ordersystem_restaurants;
CREATE TABLE stg.ordersystem_restaurants (
    id serial PRIMARY KEY,
    object_id varchar NOT NULL,
    object_value text NOT NULL,
    update_ts timestamp NOT NULL
);

-- ordersystem_users (из коллекции users)
DROP TABLE IF EXISTS stg.ordersystem_users;
CREATE TABLE stg.ordersystem_users (
    id serial PRIMARY KEY,
    object_id varchar NOT NULL,
    object_value text NOT NULL,
    update_ts timestamp NOT NULL
);