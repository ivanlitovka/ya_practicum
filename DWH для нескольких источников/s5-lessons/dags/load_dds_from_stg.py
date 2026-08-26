"""
DAG для загрузки данных из STG в DDS слой
"""
from airflow.decorators import dag, task
import logging
import pendulum

from my_lib import (
    create_postgres_engine,
    get_dds_loaded_ts,
    save_dds_loaded_state,
    load_dm_users,
    load_dm_restaurants,
    load_dm_timestamps,
    load_dm_products,
    load_dm_orders,
    load_fct_product_sales
)

log = logging.getLogger(__name__)


@task(task_id='load_dm_users')
def load_dm_users_task():
    load_dm_users(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@task(task_id='load_dm_restaurants')
def load_dm_restaurants_task():
    load_dm_restaurants(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@task(task_id='load_dm_timestamps')
def load_dm_timestamps_task():
    load_dm_timestamps(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@task(task_id='load_dm_products')
def load_dm_products_task():
    load_dm_products(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@task(task_id='load_dm_orders')
def load_dm_orders_task():
    load_dm_orders(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@task(task_id='load_fct_product_sales')
def load_fct_product_sales_task():
    load_fct_product_sales(dwh_conn_id='PG_WAREHOUSE_CONNECTION', schema='dds')


@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2026, 7, 7, tz='UTC'),
    catchup=False,
    tags=['sprint5', 'dds'],
    is_paused_upon_creation=False,
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_dds_from_stg():
    """Загрузка данных из STG в DDS слой"""
    
    users_task = load_dm_users_task()
    restaurants_task = load_dm_restaurants_task()
    timestamps_task = load_dm_timestamps_task()
    products_task = load_dm_products_task()
    orders_task = load_dm_orders_task()
    fct_sales_task = load_fct_product_sales_task()
    
    # Порядок загрузки:
    # 1. Независимые измерения → продукты → заказы → факты
    [users_task, restaurants_task, timestamps_task] >> products_task >> orders_task >> fct_sales_task


dag = load_dds_from_stg()