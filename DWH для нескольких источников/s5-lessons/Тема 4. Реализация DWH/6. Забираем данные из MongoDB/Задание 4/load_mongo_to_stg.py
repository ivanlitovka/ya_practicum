"""
DAG для загрузки данных из MongoDB в DWH
"""
from airflow.decorators import dag, task
import logging
import pendulum

from mongo_lib import extract_load_mongo_collection

log = logging.getLogger(__name__)


@task(task_id='load_restaurants')
def load_restaurants():
    """Загрузка коллекции restaurants -> stg.ordersystem_restaurants"""
    extract_load_mongo_collection(
        collection_name='restaurants',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        dwh_table='ordersystem_restaurants',
        workflow_key='mongo_restaurants_load',
        dwh_schema='stg',
        batch_size=1000,
        date_field='update_ts'
    )


@task(task_id='load_users')
def load_users():
    """Загрузка коллекции users -> stg.ordersystem_users"""
    extract_load_mongo_collection(
        collection_name='users',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        dwh_table='ordersystem_users',
        workflow_key='mongo_users_load',
        dwh_schema='stg',
        batch_size=1000,
        date_field='update_ts'
    )


@task(task_id='load_orders')
def load_orders():
    """Загрузка коллекции orders -> stg.ordersystem_orders"""
    extract_load_mongo_collection(
        collection_name='orders',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        dwh_table='ordersystem_orders',
        workflow_key='mongo_orders_load',
        dwh_schema='stg',
        batch_size=1000,
        date_field='update_ts'
    )


@dag(
    schedule_interval='*/15 * * * *',
    start_date=pendulum.datetime(2026, 8, 1, tz='UTC'),
    catchup=False,
    tags=['sprint5', 'mongodb', 'stg'],
    is_paused_upon_creation=False,
    default_args={
        'owner': 'airflow',
        'retries': 2,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_mongo_to_stg():
    """Загрузка данных из MongoDB в STG слой"""
    restaurants_task = load_restaurants()
    users_task = load_users()
    orders_task = load_orders()
    
    # Все задачи выполняются параллельно
    [restaurants_task, users_task, orders_task]


dag = load_mongo_to_stg()