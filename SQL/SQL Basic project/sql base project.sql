CREATE SCHEMA IF NOT EXISTS raw_data;

CREATE TABLE IF NOT EXISTS raw_data.sales (
	id integer,
	auto text,
	gasoline_consumption NUMERIC(4,2),
	price integer,
	date date,
	person_name text,
	phone text,
	discount integer,
	brand_origin text
	);

ALTER TABLE raw_data.sales ALTER COLUMN price SET DATA TYPE numeric(9,2);

SELECT * FROM raw_data.sales s ;

CREATE SCHEMA  IF NOT EXISTS car_shop;

-- Таблица брендов
CREATE TABLE  car_shop.brands (
	brand_id serial PRIMARY KEY,
	brand_name text NOT NULL,
	origin_country varchar(45) -- 45 самое длинное название страны в мире
	);
	
-- Таблица моделей автомобилей
CREATE TABLE car_shop.car_models (
	model_id serial PRIMARY KEY,
	brand_id int REFERENCES car_shop.brands(brand_id),
	model_name text NOT NULL,
	);

-- Таблица цветов
CREATE TABLE car_shop.colors (
	id serial PRIMARY KEY,
	color_name varchar(50) NOT NULL
	);

ALTER TABLE car_shop.car_models rename COLUMN id to model_id;

--Таблица автомобилий
CREATE TABLE car_shop.cars (
	car_id serial PRIMARY KEY,
	model_id integer REFERENCES car_shop.car_models(model_id),
	color_is
)