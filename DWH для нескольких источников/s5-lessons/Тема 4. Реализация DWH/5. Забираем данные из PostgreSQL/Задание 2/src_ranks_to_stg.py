from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.decorators import dag, task
from sqlalchemy import create_engine, text
import pandas as pd
import logging
import pendulum


log = logging.getLogger(__name__)

@task(task_id='extract_load_ranks_via_hook')
def extract_load_ranks():
    log.info('Начинаем загрузку ranks: Extract -> Load')

    #Получаем параметры соединений из Airflow
    source_conn = BaseHook.get_connection('PG_ORIGIN_BONUS_SYSTEM_CONNECTION')
    dwh_conn = BaseHook.get_connection('PG_WAREHOUSE_CONNECTION')

    #Формируем URI для SQLAlchemy (psycopg2)
    source_uri = (
        f'postgresql+psycopg2://{source_conn.login}:{source_conn.password}'
        f'@{source_conn.host}:{source_conn.port}/{source_conn.schema}'
        f'?sslmode=require'
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
    log.info('Подключаемся к DWH (PG_WAREHOUSE_CONNECTION) для загрузки....')
    try:
        dwh_engine = create_engine(dwh_uri)
    except Exception as e:
        log.error(f'Ошибка созадния подключения к DWH {e}', exc_info = True)
        raise

    with dwh_engine.begin() as conn:
        #Clear stg (full rewrite)
        log.info('Выполняем TRUNCATE TABLE stg.bonussystem_ranks RESTART IDENTITY...')
        conn.execute(text('TRUNCATE TABLE stg.bonussystem_ranks RESTART IDENTITY'))

        #Insert data
        log.info(f'Начинаем вставку {rows_count} строк в stg.bonussystem_ranks.')
        try:
            df.to_sql(
                name = 'bonussystem_ranks',
                schema = 'stg',
                con = conn,
                if_exists = 'append',
                index = False,
                chunksize = 1000,
                method = 'multi'
            )
            log.info('Данные успешно загружены в stg.bonussystem_ranks.')
        except Exception as e:
            log.error(f'Ошибка при вставке данных в DWH: {e}', exc_info = True)
            raise
        
@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2022, 5, 5, tz="UTC"),
    catchup=False,
    tags=['sprint5', '5_2', 'src_ranks_to_stg'],
    is_paused_upon_creation=False
)
def load_ranks_to_stg():
    extract_load_ranks()

dag = load_ranks_to_stg()
