from airflow.decorators import dag, task
from airflow.hook.base import BaseHook
from sqlalchemy import create_engine, text
import json
import pandas as pd
import logging
import pendulum

log = logging.getLogger(__name__)

def create_postgre_engine(conn_id: str, **engine_kwargs):
    """
    Создает SQLAlchemy engine для PostgrSQL, автоматически извлекая параметры из extra
    Args: 
        conn_id: ID соединения в Airflow
        **engine_kwargs: Дополнительные параметры для create_engine
    """
    conn = BaseHook.get_connection(conn_id)

    # Извлекаем параметры из extra
    extra_params = {}
    if conn.extra:
        try:
            extra_params = json.loads(conn.extra)
            log.debug(f'Извлечены параметры из extra для {conn_id}: {extra_params}')
        except json.JSONDecodeError:
            log.warning(f'Не удалось распарсить extra для {conn_id}: {conn.extra}')

    uri = f'postgresql+psycopg2://{conn.login}:{conn.password}@{conn.host}:{conn.port}/{conn.schema}'

    # Добавляем параметры из extra в uri
    if extra_params:
        param_str = '&'.join([f'{k}={v}' for k, v in extra_params.items()])
        uri += f'?{param_str}'

    log.debug(f'Сформирова URI для {conn_id}: {uri}')

    # Создаем engine с дополнительными настройками
    default_kwargs = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    default_kwargs.update(engine_kwargs)

    return create_engine(uri, **default_kwargs)

def extract_load_table(table_name: str):
    log.info(f'Начинаем загрузку {table_name}: Extract -> Load')

    # Создаем engine - все параметры из extra автоматически подтянутся
    src_engine = create_postgre_engine('PG_ORIGIN_BONUS_SYSTEM_CONNECTION')
    dwh_engine = create_postgre_engine('PG_WAREHOUSE_CONNECTION')

    # Extract
    log.info(f'Вычитываем данные из источника (таблица {table_name})...')
    try:
        df = pd.read_sql(f'SELECT * FROM {table_name}', con=src_engine)
    except Exception as e:
        log.error(f'Ошибка при чтении источника: {e}', exc_info=True')
        raise

    if df.empty:
        log.warning(f'В источнике нет данных (таблица {table_name})....')
        return

    rows_count = len(df)
    log.info(f'Выгружено строк из источника: {rows_count}')

    # Load
    dwh_table_name = f'bonussystem_{table_name}'

    with dwh_engine.begin() as conn:
        log.info(f'Выполняем TRUNCATE TABLE stg.{dwh_table_name} RESTART IDENTITY...')
        conn.execute(text(f'TRUNCATE TABLE stg.{dwh_table_name} RESTART IDENTITY'))

        log.info(f'Начинаем вставку {rows_count} строк в stg.{table_name}')
        try:
            df.to_sql(
                name=dwh_table_name,
                schema='stg',
                com=conn,
                if_exists='append',
                index=False,
                chunksize=1000,
                method='multi'
            )
            log.info(f'Данные успешно загружены в stg.{dwh_table_name}')
        except: Exception as e:
            log.error(f'Ошибка при вставке данных в DWH: {e}', exc_info=True)
            raise

@task(task_id='extract_load_ranks_via_hook')
def extract_load_ranks():
    return extract_load_table('ranks')

@task(task_id='extract_load_users_via_hook')
def extract_load_users():
    return extraсt_load_table('users')

@dag(
    schedule_interval='0/15 * * * *',
    start_date=pendulum.datetime(2026, 7, 7, tz='UTC'),
    catchup=False,
    tags=['sprint5', '5_2', 'ex_load_table_psql'],
    is_paused_upon_creation=False
)
def load_data_to_stg():
    rank_task = extract_load_ranks()
    users_task = extract_load_users()

    [ranks_task, users_task]

dag = load_data_to_stg