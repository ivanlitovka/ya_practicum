
delete from mart.f_activity;
delete from mart.f_daily_sales;

--d_calendar
delete from mart.d_calendar;

with all_dates as (
		select distinct to_date(date_time::TEXT,'YYYY-MM-DD') as date_time from stage.user_activity_log
		union
		select distinct to_date(date_time::TEXT,'YYYY-MM-DD') from stage.user_order_log
		union
		select distinct to_date(date_id::TEXT,'YYYY-MM-DD') from stage.customer_research
		order by date_time)
INSERT INTO mart.d_calendar (date_id, fact_date, day_num, month_num, month_name,year_num)
select 
	distinct ROW_NUMBER () OVER (
	ORDER BY date_time
	) as date_id
	,date_time as fact_date
	,EXTRACT(day from date_time)::INT as day_num
	,EXTRACT(month from date_time)::INT as month_num
	,to_char(date_time, 'Mon') as month_name
	,EXTRACT(year from date_time)::INT as year_num
from all_dates;

--d_customer
delete from mart.d_customer;

INSERT INTO mart.d_customer  (customer_id, first_name, last_name,city_id)
select distinct customer_id
		,first_name
		,last_name
		,max (city_id)
from stage.user_order_log 
group by customer_id , first_name, last_name;

--d_item
delete from mart.d_item;

INSERT INTO mart.d_item  (item_id, item_name)
select distinct item_id
		,item_name
		
from stage.user_order_log ;
