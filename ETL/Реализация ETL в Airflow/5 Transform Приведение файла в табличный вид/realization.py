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
    dag_id='552_postgresql_export_fuction',
    schedule_interval='0 0 * * *',
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    dagrun_timeout=datetime.timedelta(minutes=60),
    tags=['example', 'example2'],
    params={"example_key": "example_value"},
)
business_dt = {'dt':'2022-05-06'}


def load_file_to_pg(filename, pg_table, conn_args):
    path = '/lessons/5. Реализация ETL в Airflow/4. Extract как подключиться к хранилищу, чтобы получить файл/Задание 2/'
    df = pd.read_csv(f'{path}{filename}')
    
    cols = ','.join(df.columns)
    insert_stmt = f"INSERT INTO stage.{pg_table} ({cols}) VALUES %s"

    pg_conn = psycopg2.connect(f"dbname='{conn_args.schema}' port='{conn_args.port}' user='{conn_args.login}' host='{conn_args.host}' password='{conn_args.password}'")
    cur = pg_conn.cursor()

    psycopg2.extras.execute_values(
        cur,
        insert_stmt,
        df.values,
        template=None,
        page_size=1000
    )
    pg_conn.commit()
    print(f'Успешно загружено {len(df)} строк в stage.{pg_table}')

    cur.close()
    pg_conn.close()

files = ('customer_research.csv', 'user_activity_log.csv', 'user_order_log.csv')

conn_id = 'pg_connection'
connection = BaseHook.get_connection(conn_id)

conn_args = {
    'host': connection.host,
    'port': connection.port,
    'schema': connection.schema,
    'login': connection.login,
    'password': connection.password
}

for filename in files:
    pg_name = filename.split('.', 1)[0]

    PythonOperator(
        task_id = f'load_{pg_name}',
        python_callable = load_file_to_pg,
        op_kwargs = {
            'filename': filename,
            'pg_table': pg_name,
            'conn_args': conn_args
        },
        dag=dag,
    )
