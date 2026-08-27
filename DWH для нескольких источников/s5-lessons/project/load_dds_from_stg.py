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
    load_fct_product_sales,
    load_dm_couriers,
    load_fct_deliveries,
    update_dm_orders_courier
)

log = logging.getLogger(__name__)


@task(task_id='load_dm_users')
def load_dm_users_task():
    """Загрузка измерения dm_users из stg.ordersystem_users"""
    load_dm_users(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_dm_restaurants')
def load_dm_restaurants_task():
    """Загрузка измерения dm_restaurants из stg.ordersystem_restaurants"""
    load_dm_restaurants(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_dm_timestamps')
def load_dm_timestamps_task():
    """Загрузка измерения dm_timestamps из stg.ordersystem_orders"""
    load_dm_timestamps(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_dm_products')
def load_dm_products_task():
    """Загрузка измерения dm_products из stg.ordersystem_orders (order_items)"""
    load_dm_products(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_dm_orders')
def load_dm_orders_task():
    """Загрузка измерения dm_orders из stg.ordersystem_orders"""
    load_dm_orders(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_fct_product_sales')
def load_fct_product_sales_task():
    """Загрузка фактов продаж fct_product_sales"""
    load_fct_product_sales(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_dm_couriers')
def load_dm_couriers_task():
    """Загрузка измерения dm_couriers из stg.couriers"""
    load_dm_couriers(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='load_fct_deliveries')
def load_fct_deliveries_task():
    """Загрузка фактов доставок fct_deliveries из stg.deliveries"""
    load_fct_deliveries(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


@task(task_id='update_dm_orders_courier')
def update_dm_orders_courier_task():
    """Обновление dm_orders — проставляем courier_id"""
    update_dm_orders_courier(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='dds'
    )


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
    
    # ============================================================
    # 1. Независимые измерения (выполняются параллельно)
    # ============================================================
    users_task = load_dm_users_task()
    restaurants_task = load_dm_restaurants_task()
    timestamps_task = load_dm_timestamps_task()
    couriers_task = load_dm_couriers_task()
    
    # ============================================================
    # 2. Продукты (зависят от ресторанов)
    # ============================================================
    products_task = load_dm_products_task()
    
    # ============================================================
    # 3. Заказы (зависят от users, restaurants, timestamps)
    # ============================================================
    orders_task = load_dm_orders_task()
    
    # ============================================================
    # 4. Факты продаж (зависят от заказов и продуктов)
    # ============================================================
    fct_sales_task = load_fct_product_sales_task()
    
    # ============================================================
    # 5. Доставки (зависят от заказов и курьеров)
    # ============================================================
    deliveries_task = load_fct_deliveries_task()
    
    # ============================================================
    # 6. Обновляем courier_id в заказах
    # ============================================================
    update_orders_task = update_dm_orders_courier_task()
    
    # ============================================================
    # 7. Зависимости
    # ============================================================
    
    # 7.1. Независимые измерения → Заказы
    [users_task, restaurants_task, timestamps_task] >> orders_task
    
    # 7.2. Рестораны → Продукты
    [restaurants_task] >> products_task
    
    # 7.3. Заказы + Продукты → Факты продаж
    [orders_task, products_task] >> fct_sales_task
    
    # 7.4. Заказы + Курьеры → Доставки
    [orders_task, couriers_task] >> deliveries_task
    
    # 7.5. Доставки → Обновление courier_id в заказах
    deliveries_task >> update_orders_task


dag = load_dds_from_stg()