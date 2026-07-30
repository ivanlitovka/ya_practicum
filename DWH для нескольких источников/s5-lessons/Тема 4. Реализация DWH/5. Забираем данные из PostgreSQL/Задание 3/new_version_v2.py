from airflow.decorators import dag, task
import logging
import pendulum

# Импортируем из нашей библиотеки
from my_lib import extract_load_table

log = logging.getLogger(__name__)


@task(task_id='extract_load_ranks_via_hook')
def extract_load_ranks():
    """Загрузка таблицы ranks"""
    return extract_load_table(
        source_conn_id='PG_ORIGIN_BONUS_SYSTEM_CONNECTION',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        source_table='ranks',
        dwh_table='bonussystem_ranks',
        dwh_schema='stg'
    )


@task(task_id='extract_load_users_via_hook')
def extract_load_users():
    """Загрузка таблицы users"""
    return extract_load_table(
        source_conn_id='PG_ORIGIN_BONUS_SYSTEM_CONNECTION',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        source_table='users',
        dwh_table='bonussystem_users',
        dwh_schema='stg'
    )


@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2026, 7, 7, tz='UTC'),
    catchup=False,
    tags=['sprint5', '5_2', 'ex_load_table_psql'],
    is_paused_upon_creation=False,
    doc_md=__doc__,
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_data_to_stg():
    """Загрузка данных из источника в STG слой"""
    ranks_task = extract_load_ranks()
    users_task = extract_load_users()
    
    # Задачи могут выполняться параллельно
    # Если нужно последовательно: ranks_task >> users_task
    [ranks_task, users_task]


dag = load_data_to_stg()