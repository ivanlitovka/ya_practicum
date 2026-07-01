from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.hooks.base import BaseHook
from airflow.operators.python import PythonOperator

import datetime
import requests
import pandas as pd
import os
import psycopg2, psycopg2.extras

dag = DAG(
    dag_id='583_postgresql_mart_update',
    schedule_interval='0 0 * * *',
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    dagrun_timeout=datetime.timedelta(minutes=60),
    tags=['example', 'example2'],
    params={"example_key": "example_value"},
)
business_dt = {'dt':'2022-05-06'}

###POSTGRESQL settings###
#set postgresql connectionfrom basehook
pg_conn = BaseHook.get_connection('pg_connection')

##init test connection
conn = psycopg2.connect(f"dbname='student' port='{pg_conn.port}' user='{pg_conn.login}' host='{pg_conn.host}' password='{pg_conn.password}'")
cur = conn.cursor()
cur.close()
conn.close()




#3. обновление таблиц d по загруженным данным в staging-слой

def update_mart_d_tables(ti):
    #connection to database
    psql_conn = BaseHook.get_connection('pg_connection')
    conn = psycopg2.connect(f"dbname='student' port='{psql_conn.port}' user='{psql_conn.login}' host='{psql_conn.host}' password='{psql_conn.password}'")
    cur = conn.cursor()

    #d_calendar
    cur.execute('DELETE FROM mart.d_calendar;')
    cur.execute("""
        WITH all_dates AS (
            SELECT DISTINCT date_time AS fact_date
            FROM (
                SELECT date_time FROM stage.user_activity_log
                UNION ALL
                SELECT date_time FROM stage.user_order_log
                UNION ALL
                SELECT date_id FROM stage.customer_research
            ) AS dates
        )
        INSERT INTO mart.d_calendar (date_id, fact_date, day_num, month_num , month_name, year_num)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY fact_date) + (SELECT COALESCE(MAX(date_id), 0) FROM mart.d_calendar) AS date_id,
            fact_date,
            EXTRACT(DAY FROM fact_date) AS day_num,
            EXTRACT(MONTH FROM fact_date) AS month_num,
            TO_CHAR(fact_date, 'Month') AS month_name,
            EXTRACT(YEAR FROM fact_date) AS year_num
        FROM all_dates;
    """)
    conn.commit()


    #d_customer
    cur.execute('DELETE FROM mart.d_customer;')
    cur.execute("""
        INSERT INTO mart.d_customer (customer_id, first_name, last_name, city_id)
        SELECT
            customer_id,
            MAX(first_name) AS first_name,
            MAX(last_name) AS last_name,
            MAX(city_id) AS city_id
        FROM stage.user_order_log
        GROUP BY customer_id;
    """)
    conn.commit()


    #d_item
    cur.execute('DELETE FROM mart.d_item;')
    cur.execute("""
        INSERT INTO mart.d_item (item_id, item_name)
        SELECT DISTINCT 
            item_id,
            item_name
        FROM stage.user_order_log;
    """)
    conn.commit()

    cur.close()
    conn.close()

    return 200

#4. обновление витрин (таблицы f)
def update_mart_f_tables(ti):
    #connection to database
    psql_conn = BaseHook.get_connection('pg_connection')
    conn = psycopg2.connect(f"dbname='student' port='{psql_conn.port}' user='{psql_conn.login}' host='{psql_conn.host}' password='{psql_conn.password}'")
    cur = conn.cursor()

    #f_activity
    cur.execute('DELETE FROM mart.f_activity;')
    cur.execute("""
        INSERT INTO mart.f_activity (activity_id, date_id, click_number)
        SELECT 
            ual.action_id AS activity_id,
            dc.date_id AS date_id,
            COUNT(*) AS click_number
        FROM stage.user_activity_log ual 
        INNER JOIN mart.d_calendar dc ON ual.date_time = dc.fact_date
        GROUP BY  ual.action_id, dc.date_id
        ORDER BY dc.date_id, ual.action_id;
    """)
    conn.commit()


    #f_daily_sales
    cur.execute('DELETE FROM mart.f_daily_sales;')
    cur.execute("""
        INSERT INTO mart.f_daily_sales  (date_id, item_id, customer_id , price , quantity , payment_amount)
        SELECT
            dc.date_id AS date_id,
            uol.item_id AS item_id,
            uol.customer_id AS customer_id,
            AVG(CASE WHEN uol.quantity > 0 THEN uol.payment_amount / uol.quantity ELSE 0 END) AS price,
            SUM(uol.quantity) AS quantity,
            SUM(uol.payment_amount) AS payment_amount
        FROM stage.user_order_log uol 
        INNER JOIN mart.d_calendar dc ON uol.date_time = dc.fact_date
        GROUP BY dc.date_id, uol.item_id, uol.customer_id
        ORDER BY dc.date_id, uol.item_id, uol.customer_id;
    """)
    conn.commit()

    cur.close()
    conn.close()


    return 200


t_update_mart_d_tables = PythonOperator(task_id='update_mart_d_tables',
                                        python_callable=update_mart_d_tables,
                                        dag=dag)


t_update_mart_f_tables = PythonOperator(task_id='update_mart_f_tables',
                                        python_callable=update_mart_f_tables,
                                        dag=dag)


t_update_mart_d_tables >> t_update_mart_f_tables