"""
Библиотека для работы с данными в Airflow
"""
import json
import logging
from typing import Optional, Dict, Any

from airflow.hooks.base import BaseHook
from sqlalchemy import create_engine, text
import pandas as pd

log = logging.getLogger(__name__)


def create_postgres_engine(conn_id: str, **engine_kwargs):
    """
    Создает SQLAlchemy engine для PostgreSQL, автоматически извлекая параметры из extra
    Args:
        conn_id: ID соединения в Airflow
        **engine_kwargs: Дополнительные параметры для create_engine
    Returns:
        Engine: SQLAlchemy engine
    Examples:
        >>> engine = create_postgres_engine('PG_ORIGIN_BONUS_SYSTEM_CONNECTION')
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
    
    # Формируем URI
    uri = f'postgresql+psycopg2://{conn.login}:{conn.password}@{conn.host}:{conn.port}/{conn.schema}'
    
    # Добавляем параметры из extra в URI
    if extra_params:
        param_str = '&'.join([f'{k}={v}' for k, v in extra_params.items()])
        uri += f'?{param_str}'
    
    log.debug(f'Сформирован URI для {conn_id}: {uri}')
    
    # Настройки по умолчанию
    default_kwargs = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    default_kwargs.update(engine_kwargs)
    
    return create_engine(uri, **default_kwargs)


def extract_data(source_conn_id: str, table_name: str, query: Optional[str] = None) -> pd.DataFrame:
    """
    Извлекает данные из источника
    Args:
        source_conn_id: ID соединения в Airflow
        table_name: Название таблицы
        query: SQL запрос (если None, используется SELECT * FROM table_name)
    Returns:
        pd.DataFrame: Данные из источника
    Raises:
        Exception: При ошибке чтения данных
    """
    log.info(f'Извлекаем данные из {source_conn_id}, таблица {table_name}')
    
    try:
        engine = create_postgres_engine(source_conn_id)
        
        if query:
            df = pd.read_sql(query, con=engine)
        else:
            df = pd.read_sql(f'SELECT * FROM {table_name}', con=engine)
        
        log.info(f'Извлечено {len(df)} строк из {table_name}')
        return df
        
    except Exception as e:
        log.error(f'Ошибка при извлечении данных из {table_name}: {e}', exc_info=True)
        raise


def load_data_to_dwh(
    df: pd.DataFrame,
    dwh_conn_id: str,
    table_name: str,
    schema: str = 'stg',
    truncate: bool = True,
    chunksize: int = 1000
) -> None:
    """
    Загружает данные в DWH
    Args:
        df: DataFrame с данными
        dwh_conn_id: ID соединения с DWH
        table_name: Название таблицы в DWH
        schema: Схема в DWH
        truncate: Очищать ли таблицу перед загрузкой
        chunksize: Размер чанка для вставки
    Raises:
        Exception: При ошибке загрузки данных
    """
    if df.empty:
        log.warning('DataFrame пуст, загрузка не требуется')
        return
    
    log.info(f'Загружаем {len(df)} строк в {schema}.{table_name}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу если нужно
            if truncate:
                log.info(f'Выполняем TRUNCATE TABLE {schema}.{table_name} RESTART IDENTITY...')
                conn.execute(text(f'TRUNCATE TABLE {schema}.{table_name} RESTART IDENTITY'))
            
            # Загружаем данные
            df.to_sql(
                name=table_name,
                schema=schema,
                con=conn,
                if_exists='append',
                index=False,
                chunksize=chunksize,
                method='multi'
            )
            
            log.info(f'Данные успешно загружены в {schema}.{table_name}')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке данных в {schema}.{table_name}: {e}', exc_info=True)
        raise


def extract_load_table(
    source_conn_id: str,
    dwh_conn_id: str,
    source_table: str,
    dwh_table: Optional[str] = None,
    dwh_schema: str = 'stg',
    truncate: bool = True,
    query: Optional[str] = None,
    **kwargs
) -> None:
    """
    Основная функция для ETL: Extract + Load
    Args:
        source_conn_id: ID соединения с источником
        dwh_conn_id: ID соединения с DWH
        source_table: Название таблицы в источнике
        dwh_table: Название таблицы в DWH (если None, используется source_table)
        dwh_schema: Схема в DWH
        truncate: Очищать ли таблицу перед загрузкой
        query: SQL запрос для извлечения (если None, используется SELECT * FROM source_table)
        **kwargs: Дополнительные параметры
    """
    # Если имя таблицы в DWH не указано, используем имя из источника
    if dwh_table is None:
        dwh_table = source_table
    
    log.info(f'Начинаем загрузку {source_table} -> {dwh_schema}.{dwh_table}')
    
    # Extract
    df = extract_data(source_conn_id, source_table, query)
    
    if df.empty:
        log.warning(f'Нет данных для загрузки из {source_table}')
        return
    
    # Load
    load_data_to_dwh(
        df=df,
        dwh_conn_id=dwh_conn_id,
        table_name=dwh_table,
        schema=dwh_schema,
        truncate=truncate,
        chunksize=kwargs.get('chunksize', 1000)
    )
    
    log.info(f'Загрузка {source_table} -> {dwh_schema}.{dwh_table} завершена')


# Дополнительные утилиты
def get_connection_params(conn_id: str) -> Dict[str, Any]:
    """
    Получает параметры подключения из Airflow
    Args:
        conn_id: ID соединения в Airflow
    Returns:
        Dict: Параметры подключения
    """
    conn = BaseHook.get_connection(conn_id)
    
    params = {
        'host': conn.host,
        'port': conn.port,
        'database': conn.schema,
        'user': conn.login,
        'password': conn.password,
    }
    
    if conn.extra:
        try:
            extra_params = json.loads(conn.extra)
            params.update(extra_params)
        except json.JSONDecodeError:
            log.warning(f'Не удалось распарсить extra для {conn_id}')
    
    return params


def test_connection(conn_id: str) -> bool:
    """
    Проверяет подключение к базе данных
    Args:
        conn_id: ID соединения в Airflow
    Returns:
        bool: True если подключение успешно, иначе False
    """
    try:
        engine = create_postgres_engine(conn_id)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        log.info(f'Подключение к {conn_id} успешно')
        return True
    except Exception as e:
        log.error(f'Ошибка подключения к {conn_id}: {e}')
        return False