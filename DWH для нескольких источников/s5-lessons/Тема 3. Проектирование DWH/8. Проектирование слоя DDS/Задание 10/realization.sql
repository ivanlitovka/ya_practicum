ALTER TABLE dds.fct_product_sales
	ADD CONSTRAINT dm_fct_product_sales_product_id_fkey
	FOREIGN KEY (product_id)
	REFERENCES dds.dm_products(id),
	ADD CONSTRAINT dm_fct_product_sales_order_id_fkey
	FOREIGN KEY (order_id)
	REFERENCES dds.dm_orders(id);