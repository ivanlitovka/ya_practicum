"""
DAG для загрузки данных из DDS в CDM слой (витрина)
"""
from airflow.decorators import dag, task
import logging
import pendulum

from my_lib import (
    create_postgres_engine,
    get_dds_loaded_ts,
    save_dds_loaded_state,
    load_dm_settlement_report
)

log = logging.getLogger(__name__)


@task(task_id='load_dm_settlement_report')
def load_dm_settlement_report_task():
    """Загрузка витрины dm_settlement_report из DDS"""
    load_dm_settlement_report(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        schema='cdm'
    )


@dag(
    schedule_interval='0 0 1 * *',  # Первый день каждого месяца
    start_date=pendulum.datetime(2026, 7, 1, tz='UTC'),
    catchup=False,
    tags=['sprint5', 'cdm', 'dm_settlement_report'],
    is_paused_upon_creation=False,
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_cdm_from_dds():
    """Загрузка данных из DDS в CDM слой"""
    load_dm_settlement_report_task()


dag = load_cdm_from_dds()