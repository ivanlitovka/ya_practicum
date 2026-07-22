CREATE TABLE dds.dm_products(
	id serial NOT NULL PRIMARY KEY,
	restaurant_id int NOT NULL,
	product_id varchar NOT NULL ,
	product_name varchar NOT NULL,
	product_price NUMERIC(14,2) NOT NULL default(0) check(product_price >= 0),
	active_from timestamp NOT NULL,
	active_to timestamp NOT NULL
);