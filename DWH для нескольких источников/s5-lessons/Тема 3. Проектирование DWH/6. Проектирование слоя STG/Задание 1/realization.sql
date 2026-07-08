drop table if exists stg.bonussystem_users;
CREATE TABLE  stg.bonussystem_users(
     id integer not NULL,
    order_user_id text NOT NULL 
);

drop table if exists stg.bonussystem_ranks;

CREATE TABLE stg.bonussystem_ranks(
    id integer NOT NULL,
    name varchar(2048) NOT NULL,
    bonus_percent numeric(19,5) NOT NULL,
    min_payment_threshold numeric(19,5) NOT NULL 
);

drop table if exists stg.bonussystem_events;
CREATE TABLE stg.bonussystem_events(
    id integer NOT NULL,
    event_ts timestamp without time zone NOT NULL,
    event_type varchar NOT NULL,
    event_value text NOT NULL 
); 
drop index if exists idx_bonussystem_events__event_ts;
CREATE INDEX idx_bonussystem_events__event_ts ON stg.bonussystem_events USING btree (event_ts);