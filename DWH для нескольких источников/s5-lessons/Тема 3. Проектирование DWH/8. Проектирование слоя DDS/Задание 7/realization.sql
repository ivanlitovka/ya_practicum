CREATE TABLE dds.dm_orders(
	id serial NOT NULL PRIMARY KEY,
	order_key varchar NOT NULL,
	order_status varchar NOT NULL,
	restaurant_id int NOT NULL,
	timestamp_id int NOT NULL,
	user_id int NOT NULL
);