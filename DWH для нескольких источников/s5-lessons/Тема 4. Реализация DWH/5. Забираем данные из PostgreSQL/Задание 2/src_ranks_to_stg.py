from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from sqlalchemy import create_engine
import pandas as pd
import logging
import pendulum


log = logging.getLogger(__name__)

def extract_load_ranks():
    log.info('Начинаем загрузку ranks: Extract -> Load')

    #Получаем параметры соединений из Airflow
    source_conn = BaseHook.get_connection('PG_ORIGIN_BONUS_SYSTEM_CONNECTION')
    dwh_conn = BaseHook.get_connection('PG_WAREHOUSE_CONNECTION')

    #Формируем URI для SQLAlchemy (psycopg2)
    source_uri = (
        f'postgresql+psycopg2://{source_conn.login}:{source_conn.password}'
        f'@{source_conn.host}:{source_conn.port}/{source_conn.schema}'
    )
    dwh_uri = (
        f'postgresql+psycopg2://{dwh_conn.login}:{dwh_conn.password}'
        f'@{dwh_conn.host}:{dwh_conn.port}/{dwh_conn.schema}'
    )

    log.debug('URI источника сформирован')
    log.debug('URI DWH сформирован')

    #1. Extract: Read source
    log.info('Вычитываем данные из источника (PG_ORIGIN_BONUS_SYSTEM_CONNECTION)...')
    try:
        src_engine = create_engine(source_uri)
        df = pd.read_sql('SELECT * FROM ranks', con = src_engine)
    except Exception as e:
        log.error(f'Ошибка при чтении источника: {e}', exc_info = True)
        raise

    if df.empty:
        log.warning('В источнике  нет данных (таблица rank пуста). Загрузка не требуется.')
        return
    
    rows_count = len(df)
    log.info(f'Выгружено строк из источника: {rows_count}')

    #2. Load: TRUNCATE + INSERT in DWH

@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2022, 5, 5, tz="UTC"),
    catchup=False,
    tags=['sprint5', '5_2', 'src_ranks_to_stg'],
    is_paused_upon_creation=False
)



hello_dag = hello_world_dag()
