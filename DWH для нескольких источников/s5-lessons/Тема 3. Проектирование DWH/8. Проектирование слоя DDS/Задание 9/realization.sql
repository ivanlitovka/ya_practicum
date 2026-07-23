CREATE TABLE dds.fct_product_sales(
	id serial NOT NULL PRIMARY key,
	product_id int NOT NULL,
	order_id int NOT NULL,
	count integer NOT NULL DEFAULT(0) CHECK(count >= 0),
	price NUMERIC(14,2) NOT NULL default(0) check(price >= 0),
	total_sum numeric(14,2) NOT NULL default(0) check(total_sum >= 0),
	bonus_payment numeric(14,2) NOT NULL default(0) check(bonus_payment >= 0),
	bonus_grant numeric(14,2) NOT NULL default(0) check(bonus_grant >= 0)
);