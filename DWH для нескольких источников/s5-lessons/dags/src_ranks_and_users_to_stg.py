"""
DAG для загрузки данных из источника в DWH
"""
from airflow.decorators import dag, task
import logging
import pendulum

from my_lib import (
    extract_load_table,
    get_last_loaded_id,
    save_loaded_state
)

log = logging.getLogger(__name__)


@task(task_id='extract_load_ranks_via_hook')
def extract_load_ranks():
    """Загрузка таблицы ranks (полная перезагрузка)"""
    extract_load_table(
        source_conn_id='PG_ORIGIN_BONUS_SYSTEM_CONNECTION',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        source_table='ranks',
        dwh_table='bonussystem_ranks',
        dwh_schema='stg',
        truncate=True
    )


@task(task_id='extract_load_users_via_hook')
def extract_load_users():
    """Загрузка таблицы users (полная перезагрузка)"""
    extract_load_table(
        source_conn_id='PG_ORIGIN_BONUS_SYSTEM_CONNECTION',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        source_table='users',
        dwh_table='bonussystem_users',
        dwh_schema='stg',
        truncate=True
    )


@task(task_id='extract_load_events_via_hook')
def extract_load_events():
    """
    Загрузка таблицы outbox (инкрементальная с сохранением состояния)
    """
    log.info('Начинаем загрузку outbox -> stg.bonussystem_events')
    
    # 1. Получаем последний загруженный id из таблицы настроек
    last_id = get_last_loaded_id(
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        workflow_key='outbox_events_load',
        schema='stg',
        default=0
    )
    log.info(f'Последний загруженный id: {last_id}')
    
    # 2. Загружаем данные с фильтром по id
    df = extract_load_table(
        source_conn_id='PG_ORIGIN_BONUS_SYSTEM_CONNECTION',
        dwh_conn_id='PG_WAREHOUSE_CONNECTION',
        source_table='outbox',
        dwh_table='bonussystem_events',
        dwh_schema='stg',
        truncate=False,
        query=f'SELECT * FROM outbox WHERE id > {last_id} ORDER BY id ASC'
    )
    
    # 3. Если есть данные - сохраняем состояние
    if df is not None and not df.empty:
        new_max_id = int(df['id'].max())
        log.info(f'Новый максимальный id: {new_max_id}')
        
        save_loaded_state(
            dwh_conn_id='PG_WAREHOUSE_CONNECTION',
            workflow_key='outbox_events_load',
            last_loaded_id=new_max_id,
            schema='stg'
        )
        log.info(f'Сохранили новый last_loaded_id: {new_max_id}')
    else:
        log.info('Нет новых записей для загрузки')


@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2026, 7, 7, tz='UTC'),
    catchup=False,
    tags=['sprint5', '5_2', 'ex_load_table_psql'],
    is_paused_upon_creation=False,
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
    events_task = extract_load_events()
    
    # Все задачи выполняются параллельно
    [ranks_task, users_task, events_task]


dag = load_data_to_stg()