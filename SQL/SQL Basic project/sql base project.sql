
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

--СОздаем схему car_shop
CREATE SCHEMA  IF NOT EXISTS car_shop;

-- Таблица брендов
CREATE TABLE  car_shop.brands (
	brand_id serial PRIMARY KEY,
	brand_name text NOT NULL, /* Название бренда из любых символов */
	origin_country varchar(45) -- 45 самое длинное название страны в мире
	);
	
--Заполняем бренды
INSERT INTO car_shop.brands (brand_name, origin_country)
SELECT DISTINCT split_part(s.auto, ' ', 1), s.brand_origin 
FROM raw_data.sales s
ORDER BY 1
;

--Проверка брендов
SELECT * FROM car_shop.brands b ;


-- Таблица моделей автомобилей
CREATE TABLE car_shop.car_models (
	model_id serial PRIMARY KEY,
	brand_id int REFERENCES car_shop.brands(brand_id),
	model_name text NOT NULL /* Любые названия моделей */
	);

--Заполняем модели автомобилей
INSERT INTO car_shop.car_models (brand_id, model_name)
SELECT DISTINCT b.brand_id, --concat(split_part(split_part(s.auto, ',', 1), ' ', 2), ' ', split_part(split_part(s.auto, ',', 1), ' ', 3))
		substr(split_part(s.auto, ',', 1), (strpos(split_part(s.auto, ',', 1), ' ') + 1)) -- этот вариант пришел вторым, выглядит лаконичней, оставил его
FROM raw_data.sales s
JOIN car_shop.brands b ON split_part(s.auto, ' ', 1) = b.brand_name 
ORDER BY 1
;

--Проверка моделей
SELECT * FROM car_shop.car_models;

-- Таблица цветов
CREATE TABLE car_shop.colors (
	id serial PRIMARY KEY,
	color_name varchar(50) NOT NULL
	);

ALTER TABLE car_shop.colors rename COLUMN colors_id to color_id; -- Исправлял название id, не с первого раза

-- Заполняем цвета
INSERT INTO car_shop.colors (color_name)
SELECT DISTINCT trim(split_part(s.auto, ',', 2))
FROM raw_data.sales s
ORDER BY 1
RETURNING *;

--Таблица автомобилий
CREATE TABLE car_shop.cars (
	car_id serial PRIMARY KEY,
	model_id integer REFERENCES car_shop.car_models(model_id),
	color_id integer REFERENCES car_shop.colors(color_id),
/*	price numeric(9,2) CHECK (price > 0), 	Тут вопрос, по сути должна стоять цена без скидки. Надо ли ее расчитывать.
											Не решил как его заполнить, но и удалять не стал. UPD: Изучив повторно сырые данные пришел к выводу
											что цена у однотипных машин стоит разная, по сути при заполнении такой таблице, получим столько же
											записей сколько и в сырой, столбец удалил */
	gasoline_consumption numeric(4,2) CHECK (gasoline_consumption > 0)	/* по описанию расход двузначное число с дробью */
);

ALTER TABLE car_shop.cars DROP COLUMN price;

-- Заполняем таблицу автомобилей
INSERT INTO car_shop.cars (model_id, color_id, gasoline_consumption)
SELECT DISTINCT cm.model_id, c.color_id, s.gasoline_consumption 
FROM raw_data.sales s 
LEFT JOIN car_shop.car_models cm ON cm.model_name = substr(split_part(s.auto, ',', 1), (strpos(split_part(s.auto, ',', 1), ' ') + 1))
LEFT JOIN car_shop.colors c ON c.color_name = trim(split_part(s.auto, ',', 2))
ORDER BY 1
RETURNING *;


--Таблица клиентов
CREATE TABLE car_shop.customers (
	customer_id serial PRIMARY KEY,
	full_name text UNIQUE NOT NULL,
	phone varchar(25) UNIQUE NOT NULL
);

-- Заполняем таблицу клиентов
INSERT INTO car_shop.customers (full_name, phone)
SELECT DISTINCT s.person_name, s.phone 
FROM raw_data.sales s
ORDER BY 1;

SELECT * FROM car_shop.customers c ;

--Таблица продаж
CREATE TABLE car_shop.sales (
	sale_id serial PRIMARY KEY,
	car_id integer REFERENCES car_shop.cars(car_id),
	customer_id integer REFERENCES car_shop.customers(customer_id),
	sale_date date NOT NULL,
	discount numeric(5,2) CHECK (discount BETWEEN 0 AND 100), 
	final_price NUMERIC(9,2) CHECK (final_price > 0) /* семизначное число с дробью */
);

-- Заполняем таблицу продаж
INSERT INTO car_shop.sales (
	car_id,
	customer_id,
	sale_date,
	discount,
	final_price
)
SELECT
	car_info.car_id,
	cust.customer_id,
	s."date",
	s.discount,
	s.price 
FROM
	raw_data.sales s
LEFT JOIN (
	SELECT
		c.car_id,
		b.brand_name, --b.brand_id,
		cm.model_name, --c.model_id,
		clr.color_name --clr.color_id
	FROM
		car_shop.cars c
		JOIN car_shop.colors clr USING (color_id)
		JOIN car_shop.car_models cm USING (model_id)
		JOIN car_shop.brands b USING (brand_id)
) AS car_info
ON		car_info.brand_name = split_part(s.auto, ' ', 1)
	AND car_info.model_name = substr(split_part(s.auto, ',', 1), (strpos(split_part(s.auto, ',', 1), ' ') + 1))
	AND car_info.color_name = trim(split_part(s.auto, ',', 2))
JOIN car_shop.customers cust ON s.person_name = cust.full_name
ORDER BY "date" 
RETURNING *;

SELECT * FROM car_shop.sales s ;

--Задание 1
/* Напишите запрос, который выведет процент моделей машин, у которых нет параметра gasoline_consumption. */
SELECT ((count(*) - count(gasoline_consumption))::numeric / count(*))::numeric(4,2) * 100.0 AS nulls_percentage_gasoline_consumption
FROM car_shop.cars;

--Задание 2
/* Напишите запрос, который покажет название бренда и среднюю цену его автомобилей в разбивке по всем годам с учётом скидки.
 * Итоговый результат отсортируйте по названию бренда и году в восходящем порядке.
 * Среднюю цену округлите до второго знака после запятой. */

SELECT
	b.brand_name AS brand,
	extract(YEAR FROM s.sale_date) AS year,
	avg(s.final_price)::numeric(9,2) AS price_avg
FROM car_shop.sales s
JOIN car_shop.cars c USING (car_id)
JOIN car_shop.car_models cm USING (model_id)
JOIN car_shop.brands b USING (brand_id)
GROUP BY b.brand_name, extract(YEAR FROM s.sale_date)
ORDER BY 1
;

--Задание 3
/* Посчитайте среднюю цену всех автомобилей с разбивкой по месяцам в 2022 году с учётом скидки.
 Результат отсортируйте по месяцам в восходящем порядке.
 Среднюю цену округлите до второго знака после запятой. */

SELECT 
	MONTH, extract(YEAR FROM s.sale_date) AS year, avg(s.final_price)::numeric(9,2)
FROM 
	generate_series(1, 12, 1) AS month
JOIN car_shop.sales s ON EXTRACT(MONTH FROM s.sale_date) = month
WHERE EXTRACT(YEAR FROM s.sale_date) = 2022
GROUP BY month;


