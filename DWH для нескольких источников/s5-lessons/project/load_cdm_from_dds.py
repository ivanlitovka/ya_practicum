"""
DAG для загрузки данных из DDS в CDM слой (витрины)
"""
from airflow.decorators import dag, task
import logging
import pendulum

from my_lib import (
    create_postgres_engine,
    load_dm_settlement_report,
    load_dm_courier_ledger
)

log = logging.getLogger(__name__)


@task(task_id='load_dm_settlement_report')
def load_dm_settlement_report_task():
    """Загрузка витрины dm_settlement_report (расчёты с ресторанами)"""
    load_dm_settlement_report(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='cdm'
    )


@task(task_id='load_dm_courier_ledger')
def load_dm_courier_ledger_task():
    """Загрузка витрины dm_courier_ledger (расчёты с курьерами)"""
    load_dm_courier_ledger(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='cdm'
    )


@dag(
    schedule_interval='0 0 10 * *',  # 10-го числа каждого месяца
    start_date=pendulum.datetime(2026, 7, 10, tz='UTC'),
    catchup=False,
    tags=['sprint5', 'cdm'],
    is_paused_upon_creation=False,
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_cdm_from_dds():
    """Загрузка данных из DDS в CDM слой"""
    
    settlement_task = load_dm_settlement_report_task()
    courier_task = load_dm_courier_ledger_task()
    
    # Обе витрины загружаются параллельно
    [settlement_task, courier_task]


dag = load_cdm_from_dds()