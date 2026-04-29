

CREATE TABLE IF NOT EXISTS stage.d_city AS 
	SELECT distinct
		uol.city_id,
		uol.city_name 
	FROM stage.user_order_log uol;

 
CREATE TABLE IF NOT EXISTS stage.d_calendar (
	date_id int PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	day_num smallint NOT NULL,
	month_num smallint NOT NULL,
	month_name varchar(8) NOT NULL,
	year_num smallint NOT NULL
);
	

INSERT INTO stage.d_calendar (day_num, month_num, month_name, year_num)
	SELECT 
		extract(DOW FROM date) AS day_num,
		extract(MONTH FROM date) AS month_num,
		TO_CHAR(date, 'Mon') AS month_name,
		extract(YEAR FROM date) AS year_num
	FROM generate_series(date '2020-01-01', date '2021-12-31', INTERVAL '1 day') AS t(date);