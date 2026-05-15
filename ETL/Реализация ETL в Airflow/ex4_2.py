from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.hooks.base import BaseHook
from airflow.operators.python import PythonOperator

import datetime
import requests
import pandas as pd
import os

dag = DAG(
    dag_id='542_s3_load_example',
    schedule_interval='0 0 * * *',
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    dagrun_timeout=datetime.timedelta(minutes=60),
    tags=['example', 'example2'],
    params={"example_key": "example_value"},
)
business_dt = {'dt':'2022-05-06'}

def upload_from_s3(file_names):
    url = 'https://storage.yandexcloud.net/s3-sprint3-static/lessons/'
    for file in file_names:
        endpoint = f'{url}{file}'
        df_order_log = pd.read_csv(endpoint)
    #    print(df_order_log.to_string(index=False))
        df_order_log.to_csv(f'/lessons/5. Реализация ETL в Airflow/4. Extract как подключиться к хранилищу, чтобы получить файл/Задание 2/{endpoint.split("/")[-1]}', index=False)
        
t_upload_from_s3 = PythonOperator(task_id='upload_from_s3',
                                        python_callable=upload_from_s3,
                                        op_kwargs={'file_names' : ['customer_research.csv'
                                                                ,'user_activity_log.csv'
                                                                ,'user_order_log.csv']
                                        },
                                        dag=dag)

t_upload_from_s3 