CREATE TABLE dds.dm_restaurants(
	id serial PRIMARY KEY NOT NULL,
	restaurant_id varchar NOT NULL,
	restaurant_name varchar NOT NULL,
	active_from timestamp NOT NULL,
	active_to timestamp NOT NULL
);