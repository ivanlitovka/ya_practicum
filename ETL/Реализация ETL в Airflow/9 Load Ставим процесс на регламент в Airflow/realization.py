import datetime
import time
import psycopg2

import requests
import json
import pandas as pd
import numpy as np

from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.models.xcom import XCom

###API settings###
#set api connection from basehook
api_conn = BaseHook.get_connection('create_files_api')
#d5dg1j9kt695d30blp03.apigw.yandexcloud.net
api_endpoint = api_conn.host
#5f55e6c0-e9e5-4a9c-b313-63c01fc31460
api_token = api_conn.password

#set user constants for api
nickname = 'ewanlitovka'
cohort = 16

headers = {
    "X-API-KEY": api_conn.password,
    "X-Nickname": nickname,
    "X-Cohort": cohort
}


###POSTGRESQL settings###
#set postgresql connectionfrom basehook
psql_conn = BaseHook.get_connection('pg_connection')

##init test connection
conn = psycopg2.connect(f"dbname='student' port='{psql_conn.port}' user='{psql_conn.login}' host='{psql_conn.host}' password='{psql_conn.password}'")
cur = conn.cursor()
cur.close()
conn.close()





#запрос выгрузки файлов;
#в итоге вы получите строковый идентификатор задачи выгрузки - task_id;
#через некоторое время по другому пути сформируется ссылка на выгруженные файлы
def create_files_request(ti, api_endpoint , headers):
    method_url = '/generate_report'
    r = requests.post('https://'+api_endpoint + method_url, headers=headers)
    response_dict = json.loads(r.content)
    ti.xcom_push(key='task_id', value=response_dict['task_id'])
    print(f"task_id is {response_dict['task_id']}")
    return response_dict['task_id']



#2. проверка готовности файлов в success
#вы получите строковый идентификатор - это ссылка на файлы, которые можно скачивать
def check_report(ti, api_endpoint , headers):
    task_ids = ti.xcom_pull(key='task_id', task_ids=['create_files_request'])
    task_id = task_ids[0]
    
    method_url = '/get_report'
    payload = {'task_id': task_id}

    #отчёт выгружается 60 секунд минимум;
		#погрузите DAG в сон на 70 секун и сделайте 4 итерации;
		#если отчёт не выгрузился, то должно появится предупреждение об ошибке;
    #если появилась ошибка, значит, что-то не так с выгрузкой по API;
		#чтобы определить ошибку, надо разобраться с генерацией данных;
		#ошибки с выгрузкой встречаются и на практике
    for i in range(4):
        time.sleep(70)
        r = requests.get('https://' + api_endpoint + method_url, params=payload, headers=headers)
        response_dict = json.loads(r.content)
        print(i, response_dict['status'])
        if response_dict['status'] == 'SUCCESS':
            report_id = response_dict['data']['report_id']
            break
    
    #если report_id не объявлен и success не было, то здесь возникнет ошибка
    ti.xcom_push(key='report_id', value=report_id)
    print(f"report_id is {report_id}")
    return report_id




#3. загружаем 3 файла в таблицы stage
def upload_from_s3_to_pg(ti,nickname,cohort):
    report_ids = ti.xcom_pull(key='report_id', task_ids=['check_ready_report'])
    report_id = report_ids[0]

    storage_url = 'https://storage.yandexcloud.net/s3-sprint3/cohort_{COHORT_NUMBER}/{NICKNAME}/{REPORT_ID}/{FILE_NAME}'

    personal_storage_url = storage_url.replace("{COHORT_NUMBER}", cohort)
    personal_storage_url = personal_storage_url.replace("{NICKNAME}", nickname)
    personal_storage_url = personal_storage_url.replace("{REPORT_ID}", report_id)


    #insert to database
    psql_conn = BaseHook.get_connection('pg_connection')
    conn = psycopg2.connect(f"dbname='de' port='{psql_conn.port}' user='{psql_conn.login}' host='{psql_conn.host}' password='{psql_conn.password}'")
    cur = conn.cursor()

    #get custom_research
    df_customer_research = pd.read_csv(personal_storage_url.replace("{FILE_NAME}", "customer_research.csv") )
    df_customer_research.reset_index(drop = True, inplace = True)
    insert_cr = "insert into stage.customer_research (date_id,category_id,geo_id,sales_qty,sales_amt) VALUES {cr_val};"
    i = 0
    step = int(df_customer_research.shape[0] / 100)
    while i <= df_customer_research.shape[0]:
        print('df_customer_research' , i, end='\r')
        
        cr_val =  str([tuple(x) for x in df_customer_research.loc[i:i + step].to_numpy()])[1:-1]
        cur.execute(insert_cr.replace('{cr_val}',cr_val))
        conn.commit()
        
        i += step+1

    #get order log
    df_order_log = pd.read_csv(personal_storage_url.replace("{FILE_NAME}", "user_order_log.csv") )
    df_order_log.reset_index(drop = True, inplace = True)
    insert_uol = "insert into stage.user_order_log (date_time, city_id, city_name, customer_id, first_name, last_name, item_id, item_name, quantity, payment_amount) VALUES {uol_val};"
    i = 0
    step = int(df_order_log.shape[0] / 100)
    while i <= df_order_log.shape[0]:
        print('df_order_log',i, end='\r')
        
        uol_val =  str([tuple(x) for x in df_order_log.drop(columns = ['id'] , axis = 1).loc[i:i + step].to_numpy()])[1:-1]
        cur.execute(insert_uol.replace('{uol_val}',uol_val))
        conn.commit()
        
        
        i += step+1

    #get activity log
    df_activity_log = pd.read_csv(personal_storage_url.replace("{FILE_NAME}", "user_activity_log.csv") )
    df_activity_log.reset_index(drop = True, inplace = True)
    insert_ual = "insert into stage.user_activity_log (date_time, action_id, customer_id, quantity) VALUES {ual_val};"
    i = 0
    step = int(df_activity_log.shape[0] / 100)
    while i <= df_activity_log.shape[0]:
        print('df_activity_log',i, end='\r')
        
        if df_activity_log.drop(columns = ['id'] , axis = 1).loc[i:i + step].shape[0] > 0:
            ual_val =  str([tuple(x) for x in df_activity_log.drop(columns = ['id'] , axis = 1).loc[i:i + step].to_numpy()])[1:-1]
            cur.execute(insert_ual.replace('{ual_val}',ual_val))
            conn.commit()
        
        
        i += step+1


    cur.close()
    conn.close()

    
    return 200


#3. обновление таблиц d по загруженным в staging-слой данным
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





#объявление DAG
dag = DAG(
    dag_id='591_full_dag',
    schedule_interval='0 0 * * *',
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    dagrun_timeout=datetime.timedelta(minutes=60)
)




t_file_request = PythonOperator(task_id = 'file_request',
                                        python_callable = create_files_request,
                                        op_kwargs = {
                                            'api_endpoint' : api_endpoint,
                                            'headers' : headers
                                        },
                                        dag=dag)

t_check_report = PythonOperator(task_id = 'check_report',
                                        python_callable = check_report,
                                        op_kwargs = {
                                            'api_endpoint' : api_endpoint,
                                            'headers' : headers
                                        },
                                        dag=dag)

t_upload_from_s3_to_pg = PythonOperator(task_id = 'upload_from_s3_to_pg',
                                        python_callable = check_report,
                                        op_kwargs = {
                                            'api_endpoint' : api_endpoint,
                                            'headers' : headers
                                        },
                                        dag=dag)

t_update_mart_d_tables = PythonOperator(task_id='update_mart_d_tables',
                                        python_callable=update_mart_d_tables,
                                        dag=dag)


t_update_mart_f_tables = PythonOperator(task_id='update_mart_f_tables',
                                        python_callable=update_mart_f_tables,
                                        dag=dag)

t_file_request >> t_check_report >> t_upload_from_s3_to_pg >> t_update_mart_d_tables >> t_update_mart_f_tables