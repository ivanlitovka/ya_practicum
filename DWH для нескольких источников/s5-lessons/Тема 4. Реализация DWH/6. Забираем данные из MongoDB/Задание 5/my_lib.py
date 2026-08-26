"""
Библиотека для работы с данными в Airflow
"""
import json
import logging
from typing import Optional, Any, Dict

from airflow.hooks.base import BaseHook
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd

log = logging.getLogger(__name__)


def create_postgres_engine(conn_id: str, **engine_kwargs) -> Engine:
    """
    Создает SQLAlchemy engine для PostgreSQL, автоматически извлекая параметры из extra
    
    Args:
        conn_id: ID соединения в Airflow
        **engine_kwargs: Дополнительные параметры для create_engine
    
    Returns:
        Engine: SQLAlchemy engine
    """
    conn = BaseHook.get_connection(conn_id)
    
    extra_params = {}
    if conn.extra:
        try:
            extra_params = json.loads(conn.extra)
            log.debug(f'Извлечены параметры из extra для {conn_id}: {extra_params}')
        except json.JSONDecodeError:
            log.warning(f'Не удалось распарсить extra для {conn_id}: {conn.extra}')
    
    uri = f'postgresql+psycopg2://{conn.login}:{conn.password}@{conn.host}:{conn.port}/{conn.schema}'
    
    if extra_params:
        param_str = '&'.join([f'{k}={v}' for k, v in extra_params.items()])
        uri += f'?{param_str}'
    
    log.debug(f'Сформирован URI для {conn_id}: {uri}')
    
    default_kwargs = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    default_kwargs.update(engine_kwargs)
    
    return create_engine(uri, **default_kwargs)


def extract_data(source_conn_id: str, query: str) -> pd.DataFrame:
    """
    Извлекает данные из источника по переданному запросу
    
    Args:
        source_conn_id: ID соединения в Airflow
        query: SQL запрос
    
    Returns:
        pd.DataFrame: Данные из источника
    """
    log.info(f'Извлекаем данные из {source_conn_id}')
    log.debug(f'Запрос: {query}')
    
    try:
        engine = create_postgres_engine(source_conn_id)
        df = pd.read_sql(query, con=engine)
        log.info(f'Извлечено {len(df)} строк')
        return df
    except Exception as e:
        log.error(f'Ошибка при извлечении данных: {e}', exc_info=True)
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
    """
    if df.empty:
        log.warning('DataFrame пуст, загрузка не требуется')
        return
    
    log.info(f'Загружаем {len(df)} строк в {schema}.{table_name}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            if truncate:
                log.info(f'Выполняем TRUNCATE TABLE {schema}.{table_name} RESTART IDENTITY...')
                conn.execute(text(f'TRUNCATE TABLE {schema}.{table_name} RESTART IDENTITY'))
            
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
) -> Optional[pd.DataFrame]:
    """
    Универсальная функция для ETL: Extract + Load
    
    Args:
        source_conn_id: ID соединения с источником
        dwh_conn_id: ID соединения с DWH
        source_table: Название таблицы в источнике
        dwh_table: Название таблицы в DWH (если None, используется source_table)
        dwh_schema: Схема в DWH
        truncate: Очищать ли таблицу перед загрузкой
        query: SQL запрос для извлечения (если None, используется SELECT * FROM source_table)
        **kwargs: Дополнительные параметры
    
    Returns:
        Optional[pd.DataFrame]: Загруженный DataFrame (если нужно)
    """
    if dwh_table is None:
        dwh_table = source_table
    
    log.info(f'Начинаем загрузку {source_table} -> {dwh_schema}.{dwh_table}')
    
    if query is None:
        query = f'SELECT * FROM {source_table}'
    
    df = extract_data(source_conn_id, query)
    
    if df.empty:
        log.warning(f'Нет данных для загрузки из {source_table}')
        return df
    
    load_data_to_dwh(
        df=df,
        dwh_conn_id=dwh_conn_id,
        table_name=dwh_table,
        schema=dwh_schema,
        truncate=truncate,
        chunksize=kwargs.get('chunksize', 1000)
    )
    
    log.info(f'Загрузка {source_table} -> {dwh_schema}.{dwh_table} завершена')
    
    return df


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ СО СОСТОЯНИЕМ ====================

def get_last_loaded_id(
    dwh_conn_id: str,
    workflow_key: str,
    schema: str = 'stg',
    default: int = 0
) -> int:
    """
    Получает последний загруженный id из таблицы srv_wf_settings
    
    Args:
        dwh_conn_id: ID соединения с DWH
        workflow_key: Ключ задачи
        schema: Схема таблицы
        default: Значение по умолчанию, если запись не найдена
    
    Returns:
        int: Последний загруженный id
    """
    log.info(f'Получаем последний загруженный id для workflow: {workflow_key}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        query = text(f"""
            SELECT workflow_settings 
            FROM {schema}.srv_wf_settings 
            WHERE workflow_key = :workflow_key
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {'workflow_key': workflow_key}).fetchone()
            
            if result and result[0]:
                settings = result[0]
                last_id = settings.get('last_loaded_id', default)
                last_id = int(last_id)
                log.info(f'Найден last_loaded_id: {last_id}')
                return last_id
            else:
                log.info(f'Запись не найдена, возвращаем default: {default}')
                return default
    except Exception as e:
        log.error(f'Ошибка при получении last_loaded_id: {e}', exc_info=True)
        raise


def save_loaded_state(
    dwh_conn_id: str,
    workflow_key: str,
    last_loaded_id: int,
    schema: str = 'stg'
) -> None:
    """
    Сохраняет состояние загрузки в таблицу srv_wf_settings
    
    Args:
        dwh_conn_id: ID соединения с DWH
        workflow_key: Ключ задачи
        last_loaded_id: Последний загруженный id
        schema: Схема таблицы
    """
    # Преобразуем в int на всякий случай
    last_loaded_id = int(last_loaded_id)
    
    log.info(f'Сохраняем состояние для workflow: {workflow_key}, last_loaded_id: {last_loaded_id}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        check_query = text(f"""
            SELECT id FROM {schema}.srv_wf_settings 
            WHERE workflow_key = :workflow_key
        """)
        
        with engine.begin() as conn:
            exists = conn.execute(check_query, {'workflow_key': workflow_key}).fetchone()
            
            settings = json.dumps({'last_loaded_id': last_loaded_id})
            
            if exists:
                # Обновляем существующую запись (без updated_at)
                update_query = text(f"""
                    UPDATE {schema}.srv_wf_settings 
                    SET workflow_settings = :settings
                    WHERE workflow_key = :workflow_key
                """)
                conn.execute(update_query, {
                    'settings': settings,
                    'workflow_key': workflow_key
                })
                log.info(f'Обновлена запись для {workflow_key}')
            else:
                # Создаем новую запись
                insert_query = text(f"""
                    INSERT INTO {schema}.srv_wf_settings (workflow_key, workflow_settings)
                    VALUES (:workflow_key, :settings)
                """)
                conn.execute(insert_query, {
                    'workflow_key': workflow_key,
                    'settings': settings
                })
                log.info(f'Создана новая запись для {workflow_key}')
    except Exception as e:
        log.error(f'Ошибка при сохранении состояния: {e}', exc_info=True)
        raise


def get_max_id_from_table(
    dwh_conn_id: str,
    table_name: str,
    schema: str = 'stg',
    id_column: str = 'id'
) -> int:
    """
    Получает максимальный id из указанной таблицы в DWH
    
    Args:
        dwh_conn_id: ID соединения с DWH
        table_name: Название таблицы
        schema: Схема таблицы
        id_column: Название колонки с id
    
    Returns:
        int: Максимальный id (0 если таблица пуста)
    """
    log.info(f'Получаем MAX({id_column}) из {schema}.{table_name}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        query = text(f"""
            SELECT COALESCE(MAX({id_column}), 0) as max_id
            FROM {schema}.{table_name}
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query).fetchone()
            max_id = int(result[0]) if result else 0
            log.info(f'MAX({id_column}) = {max_id}')
            return max_id
    except Exception as e:
        log.error(f'Ошибка при получении MAX(id) из {schema}.{table_name}: {e}', exc_info=True)
        raise


def execute_query(
    dwh_conn_id: str,
    query: str,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Выполняет произвольный SQL запрос
    
    Args:
        dwh_conn_id: ID соединения с DWH
        query: SQL запрос
        params: Параметры запроса
    
    Returns:
        Any: Результат запроса
    """
    log.debug(f'Выполняем запрос: {query}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result
    except Exception as e:
        log.error(f'Ошибка при выполнении запроса: {e}', exc_info=True)
        raise