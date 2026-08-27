"""
Библиотека для работы с данными в Airflow
"""
import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime

from airflow.hooks.base import BaseHook
from airflow.models import Variable
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd
from dateutil import parser
from bson import json_util

log = logging.getLogger(__name__)


def create_postgres_engine(conn_id: str, **engine_kwargs) -> Engine:
    """
    Создает SQLAlchemy engine для PostgreSQL, автоматически извлекая параметры из extra
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


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ СО СОСТОЯНИЕМ (STG) ====================

def get_last_loaded_id(
    dwh_conn_id: str,
    workflow_key: str,
    schema: str = 'stg',
    default: int = 0
) -> int:
    """
    Получает последний загруженный id из таблицы srv_wf_settings (для STG)
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
    Сохраняет состояние загрузки в таблицу srv_wf_settings (для STG)
    """
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


# ==================== ФУНКЦИИ ДЛЯ DDS ====================

def get_dds_loaded_ts(
    dwh_conn_id: str,
    workflow_key: str,
    schema: str = 'dds',
    default: str = '1970-01-01T00:00:00.000Z'
) -> datetime:
    """
    Получает последнюю загруженную дату из dds.srv_wf_settings
    """
    log.info(f'Получаем последнюю загруженную дату для workflow: {workflow_key}')
    
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
                last_ts_str = settings.get('last_loaded_ts')
                if last_ts_str:
                    log.info(f'Найдена last_loaded_ts: {last_ts_str}')
                    return parser.parse(last_ts_str)
                else:
                    log.info(f'Запись найдена, но нет last_loaded_ts, используем default')
                    return parser.parse(default)
            else:
                log.info(f'Запись не найдена, используем default')
                return parser.parse(default)
    except Exception as e:
        log.error(f'Ошибка при получении last_loaded_ts: {e}', exc_info=True)
        raise


def save_dds_loaded_state(
    dwh_conn_id: str,
    workflow_key: str,
    last_loaded_ts: datetime,
    schema: str = 'dds'
) -> None:
    """
    Сохраняет состояние загрузки в dds.srv_wf_settings
    """
    last_loaded_ts_str = last_loaded_ts.isoformat()
    
    log.info(f'Сохраняем состояние для workflow: {workflow_key}, last_loaded_ts: {last_loaded_ts_str}')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        check_query = text(f"""
            SELECT id FROM {schema}.srv_wf_settings 
            WHERE workflow_key = :workflow_key
        """)
        
        with engine.begin() as conn:
            exists = conn.execute(check_query, {'workflow_key': workflow_key}).fetchone()
            
            settings = json.dumps({'last_loaded_ts': last_loaded_ts_str})
            
            if exists:
                update_query = text(f"""
                    UPDATE {schema}.srv_wf_settings 
                    SET workflow_settings = :settings::json
                    WHERE workflow_key = :workflow_key
                """)
                conn.execute(update_query, {
                    'settings': settings,
                    'workflow_key': workflow_key
                })
                log.info(f'Обновлена запись для {workflow_key}')
            else:
                insert_query = text(f"""
                    INSERT INTO {schema}.srv_wf_settings (workflow_key, workflow_settings)
                    VALUES (:workflow_key, :settings::json)
                """)
                conn.execute(insert_query, {
                    'workflow_key': workflow_key,
                    'settings': settings
                })
                log.info(f'Создана новая запись для {workflow_key}')
    except Exception as e:
        log.error(f'Ошибка при сохранении состояния: {e}', exc_info=True)
        raise


def load_dm_users(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_users из stg.ordersystem_users
    """
    log.info('Начинаем загрузку dm_users из stg.ordersystem_users')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # 1. Очищаем таблицу
            log.info('Очищаем dds.dm_users')
            conn.execute(text('TRUNCATE TABLE dds.dm_users RESTART IDENTITY CASCADE'))
            
            # 2. Вставляем данные
            query = text("""
                INSERT INTO dds.dm_users (user_id, user_name, user_login)
                SELECT DISTINCT
                    object_id as user_id,
                    object_value::json->>'name' as user_name,
                    object_value::json->>'login' as user_login
                FROM stg.ordersystem_users
                WHERE object_id IS NOT NULL
            """)
            
            result = conn.execute(query)
            log.info(f'Загружено {result.rowcount} записей в dm_users')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_users: {e}', exc_info=True)
        raise

def load_dm_restaurants(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_restaurants из stg.ordersystem_restaurants
    
    Источник: stg.ordersystem_restaurants
    Приемник: dds.dm_restaurants
    
    SCD-2: активная запись имеет active_to = '2099-12-31'
    """
    log.info('Начинаем загрузку dm_restaurants из stg.ordersystem_restaurants')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # 1. Закрываем старые записи, которые реально изменились
            close_query = text("""
                WITH src AS (
                    SELECT DISTINCT
                        object_id as restaurant_id,
                        object_value::json->>'name' as restaurant_name,
                        update_ts
                    FROM stg.ordersystem_restaurants
                    WHERE object_id IS NOT NULL
                )
                UPDATE dds.dm_restaurants
                SET active_to = src.update_ts
                FROM src
                WHERE dm_restaurants.restaurant_id = src.restaurant_id
                AND dm_restaurants.active_to = '2099-12-31 00:00:00'
                AND (
                    dm_restaurants.restaurant_name != src.restaurant_name
                    OR dm_restaurants.active_from != src.update_ts
                )
                AND NOT EXISTS (
                    SELECT 1 
                    FROM dds.dm_restaurants existing
                    WHERE existing.restaurant_id = src.restaurant_id
                    AND existing.active_from = src.update_ts
                    AND existing.active_to = '2099-12-31 00:00:00'
                )
            """)
            
            closed_count = conn.execute(close_query)
            log.info(f'Закрыто {closed_count.rowcount} старых записей в dm_restaurants')
            
            # 2. Вставляем новые записи (только если их еще нет)
            insert_query = text("""
                INSERT INTO dds.dm_restaurants (restaurant_id, restaurant_name, active_from, active_to)
                SELECT DISTINCT
                    object_id as restaurant_id,
                    object_value::json->>'name' as restaurant_name,
                    update_ts as active_from,
                    '2099-12-31 00:00:00'::timestamp as active_to
                FROM stg.ordersystem_restaurants
                WHERE object_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 
                    FROM dds.dm_restaurants 
                    WHERE dm_restaurants.restaurant_id = stg.ordersystem_restaurants.object_id
                    AND dm_restaurants.active_from = stg.ordersystem_restaurants.update_ts
                )
            """)
            
            insert_result = conn.execute(insert_query)
            log.info(f'Вставлено {insert_result.rowcount} новых записей в dm_restaurants')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_restaurants: {e}', exc_info=True)
        raise

def load_dm_timestamps(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_timestamps из stg.ordersystem_orders
    """
    log.info('Начинаем загрузку dm_timestamps из stg.ordersystem_orders')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            query = text("""
                INSERT INTO dds.dm_timestamps (ts, year, month, day, time, date)
                SELECT DISTINCT
                    ts,
                    EXTRACT(YEAR FROM ts)::int as year,
                    EXTRACT(MONTH FROM ts)::int as month,
                    EXTRACT(DAY FROM ts)::int as day,
                    ts::time as time,
                    ts::date as date
                FROM (
                    SELECT DISTINCT
                        date_trunc('second', (TO_TIMESTAMP((object_value::json->'date'->>'$date')::bigint / 1000.0))::timestamp) as ts
                    FROM stg.ordersystem_orders
                    WHERE object_value::json->>'final_status' IN ('CLOSED', 'CANCELLED')
                    AND object_value::json->'date'->>'$date' IS NOT NULL
                ) src
                WHERE ts IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 
                    FROM dds.dm_timestamps 
                    WHERE dm_timestamps.ts = src.ts
                )
            """)
            
            result = conn.execute(query)
            log.info(f'Вставлено {result.rowcount} новых записей в dm_timestamps')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_timestamps: {e}', exc_info=True)
        raise

def load_dm_products(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_products из stg.ordersystem_orders
    
    Источник: stg.ordersystem_orders (поле order_items)
    Приемник: dds.dm_products
    
    Логика: только уникальные product_id (без историчности)
    """
    log.info('Начинаем загрузку dm_products из stg.ordersystem_orders')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # 1. Очищаем таблицу (полная перезагрузка)
            log.info('Очищаем dds.dm_products')
            conn.execute(text('TRUNCATE TABLE dds.dm_products RESTART IDENTITY CASCADE'))
            
            # 2. Вставляем уникальные продукты
            insert_query = text("""
                INSERT INTO dds.dm_products (
                    restaurant_id,
                    product_id,
                    product_name,
                    product_price,
                    active_from,
                    active_to
                )
                SELECT DISTINCT ON (product_id)
                    dm_restaurants.id as restaurant_id,
                    src.product_id,
                    src.product_name,
                    src.product_price,
                    CURRENT_TIMESTAMP as active_from,
                    '2099-12-31 00:00:00'::timestamp as active_to
                FROM (
                    SELECT 
                        orders.object_value::json->'restaurant'->'id'->>'$oid' as restaurant_oid,
                        item->'id'->>'$oid' as product_id,
                        item->>'name' as product_name,
                        (item->>'price')::numeric as product_price
                    FROM stg.ordersystem_orders orders,
                         json_array_elements(orders.object_value::json->'order_items') as item
                    WHERE orders.object_value::json->>'final_status' IN ('CLOSED', 'CANCELLED')
                ) src
                JOIN dds.dm_restaurants 
                    ON dm_restaurants.restaurant_id = src.restaurant_oid
                    AND dm_restaurants.active_to = '2099-12-31 00:00:00'
                GROUP BY dm_restaurants.id, src.product_id, src.product_name, src.product_price
            """)
            
            result = conn.execute(insert_query)
            log.info(f'Вставлено {result.rowcount} записей в dm_products')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_products: {e}', exc_info=True)
        raise

def load_dm_orders(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_orders из stg.ordersystem_orders
    
    Источник: stg.ordersystem_orders
    Приемник: dds.dm_orders
    
    Берем заказы с final_status IN ('CLOSED', 'CANCELLED')
    """
    log.info('Начинаем загрузку dm_orders из stg.ordersystem_orders')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу (полная перезагрузка)
            log.info('Очищаем dds.dm_orders')
            conn.execute(text('TRUNCATE TABLE dds.dm_orders RESTART IDENTITY CASCADE'))
            
            # Вставляем заказы
            insert_query = text("""
                INSERT INTO dds.dm_orders (
                    order_key,
                    order_status,
                    restaurant_id,
                    timestamp_id,
                    user_id
                )
                SELECT 
                    src.order_key,
                    src.order_status,
                    dm_restaurants.id as restaurant_id,
                    dm_timestamps.id as timestamp_id,
                    dm_users.id as user_id
                FROM (
                    SELECT 
                        object_id as order_key,
                        object_value::json->>'final_status' as order_status,
                        object_value::json->'restaurant'->'id'->>'$oid' as restaurant_oid,
                        TO_TIMESTAMP((object_value::json->'date'->>'$date')::bigint / 1000.0)::timestamp as order_ts,
                        object_value::json->'user'->'id'->>'$oid' as user_oid
                    FROM stg.ordersystem_orders
                    WHERE object_value::json->>'final_status' IN ('CLOSED', 'CANCELLED')
                ) src
                JOIN dds.dm_restaurants 
                    ON dm_restaurants.restaurant_id = src.restaurant_oid
                    AND dm_restaurants.active_to = '2099-12-31 00:00:00'
                JOIN dds.dm_timestamps 
                    ON dm_timestamps.ts = date_trunc('second', src.order_ts)
                JOIN dds.dm_users 
                    ON dm_users.user_id = src.user_oid
            """)
            
            result = conn.execute(insert_query)
            log.info(f'Вставлено {result.rowcount} записей в dm_orders')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_orders: {e}', exc_info=True)
        raise

def load_fct_product_sales(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает фактовую таблицу fct_product_sales из stg.ordersystem_orders
    """
    log.info('Начинаем загрузку fct_product_sales из stg.ordersystem_orders')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу
            log.info('Очищаем dds.fct_product_sales')
            conn.execute(text('TRUNCATE TABLE dds.fct_product_sales RESTART IDENTITY CASCADE'))
            
            # Вставляем факты (без CROSS JOIN LATERAL)
            insert_query = text("""
                INSERT INTO dds.fct_product_sales (
                    product_id,
                    order_id,
                    count,
                    price,
                    total_sum,
                    bonus_payment,
                    bonus_grant
                )
                SELECT 
                    dm_products.id as product_id,
                    dm_orders.id as order_id,
                    src.item_count as count,
                    src.item_price as price,
                    src.item_total as total_sum,
                    ROUND(
                        CASE 
                            WHEN src.order_total > 0 
                            THEN src.bonus_payment * (src.item_total / src.order_total)
                            ELSE 0 
                        END, 5
                    ) as bonus_payment,
                    ROUND(
                        CASE 
                            WHEN src.order_total > 0 
                            THEN src.bonus_grant * (src.item_total / src.order_total)
                            ELSE 0 
                        END, 5
                    ) as bonus_grant
                FROM (
                    SELECT 
                        orders.object_id as order_key,
                        (orders.object_value::json->>'bonus_payment')::numeric as bonus_payment,
                        (orders.object_value::json->>'bonus_grant')::numeric as bonus_grant,
                        item->'id'->>'$oid' as product_id,
                        (item->>'quantity')::int as item_count,
                        (item->>'price')::numeric as item_price,
                        ((item->>'quantity')::int * (item->>'price')::numeric) as item_total,
                        SUM((item->>'quantity')::int * (item->>'price')::numeric) OVER (PARTITION BY orders.object_id) as order_total
                    FROM stg.ordersystem_orders orders,
                         json_array_elements(orders.object_value::json->'order_items') as item
                    WHERE orders.object_value::json->>'final_status' IN ('CLOSED', 'CANCELLED')
                ) src
                JOIN dds.dm_orders 
                    ON dm_orders.order_key = src.order_key
                JOIN dds.dm_products 
                    ON dm_products.product_id = src.product_id
                    AND dm_products.active_to = '2099-12-31 00:00:00'
            """)
            
            result = conn.execute(insert_query)
            log.info(f'Вставлено {result.rowcount} записей в fct_product_sales')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке fct_product_sales: {e}', exc_info=True)
        raise

def load_dm_settlement_report(
    dwh_conn_id: str,
    schema: str = 'cdm'
) -> None:
    """
    Загружает витрину dm_settlement_report из DDS слоя
    
    Источник: dds (dm_orders, dm_restaurants, dm_timestamps, fct_product_sales)
    Приемник: cdm.dm_settlement_report
    
    Логика:
    - Только заказы с final_status = 'CLOSED'
    - Группировка по ресторану и месяцу (settlement_date)
    - Расчет:
        - orders_count = количество заказов
        - orders_total_sum = общая сумма заказов
        - orders_bonus_payment_sum = сумма оплат бонусами
        - orders_bonus_granted_sum = сумма начисленных бонусов
        - order_processing_fee = orders_total_sum * 0.25
        - restaurant_reward_sum = orders_total_sum - orders_bonus_payment_sum - order_processing_fee
    """
    log.info('Начинаем загрузку dm_settlement_report из DDS')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу (полная перезагрузка)
            log.info('Очищаем cdm.dm_settlement_report')
            conn.execute(text('TRUNCATE TABLE cdm.dm_settlement_report RESTART IDENTITY CASCADE'))
            
            # Вставляем данные
            insert_query = text("""
                INSERT INTO cdm.dm_settlement_report (
                    restaurant_id,
                    restaurant_name,
                    settlement_date,
                    orders_count,
                    orders_total_sum,
                    orders_bonus_payment_sum,
                    orders_bonus_granted_sum,
                    order_processing_fee,
                    restaurant_reward_sum
                )
                SELECT 
                    dm_restaurants.restaurant_id,
                    dm_restaurants.restaurant_name,
                    DATE_TRUNC('month', dm_timestamps.ts)::date as settlement_date,
                    COUNT(DISTINCT dm_orders.id) as orders_count,
                    COALESCE(SUM(fct.total_sum), 0) as orders_total_sum,
                    COALESCE(SUM(fct.bonus_payment), 0) as orders_bonus_payment_sum,
                    COALESCE(SUM(fct.bonus_grant), 0) as orders_bonus_granted_sum,
                    COALESCE(SUM(fct.total_sum), 0) * 0.25 as order_processing_fee,
                    COALESCE(SUM(fct.total_sum), 0) 
                        - COALESCE(SUM(fct.bonus_payment), 0) 
                        - COALESCE(SUM(fct.total_sum), 0) * 0.25 as restaurant_reward_sum
                FROM dds.dm_orders
                JOIN dds.dm_restaurants 
                    ON dm_orders.restaurant_id = dm_restaurants.id
                JOIN dds.dm_timestamps 
                    ON dm_orders.timestamp_id = dm_timestamps.id
                LEFT JOIN dds.fct_product_sales fct
                    ON dm_orders.id = fct.order_id
                WHERE dm_orders.order_status = 'CLOSED'
                GROUP BY 
                    dm_restaurants.restaurant_id,
                    dm_restaurants.restaurant_name,
                    DATE_TRUNC('month', dm_timestamps.ts)::date
                ORDER BY 
                    settlement_date DESC,
                    restaurant_id
            """)
            
            result = conn.execute(insert_query)
            log.info(f'Вставлено {result.rowcount} записей в dm_settlement_report')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_settlement_report: {e}', exc_info=True)
        raise

def load_dm_couriers(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает измерение dm_couriers из stg.couriers
    """
    log.info('Начинаем загрузку dm_couriers из stg.couriers')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу
            conn.execute(text('TRUNCATE TABLE dds.dm_couriers RESTART IDENTITY CASCADE'))
            
            # Вставляем курьеров
            query = text("""
                INSERT INTO dds.dm_couriers (courier_id, courier_name)
                SELECT courier_id, courier_name
                FROM stg.couriers
                ON CONFLICT (courier_id) DO UPDATE SET
                    courier_name = EXCLUDED.courier_name
            """)
            
            result = conn.execute(query)
            log.info(f'Загружено {result.rowcount} курьеров в dm_couriers')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_couriers: {e}', exc_info=True)
        raise


def load_fct_deliveries(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Загружает факт доставок fct_deliveries из stg.deliveries
    """
    log.info('Начинаем загрузку fct_deliveries из stg.deliveries')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            # Очищаем таблицу
            conn.execute(text('TRUNCATE TABLE dds.fct_deliveries RESTART IDENTITY CASCADE'))
            
            # Вставляем доставки
            query = text("""
                INSERT INTO dds.fct_deliveries (
                    order_id,
                    courier_id,
                    delivery_ts,
                    rate,
                    tip_sum
                )
                SELECT 
                    dm_orders.id as order_id,
                    dm_couriers.id as courier_id,
                    stg.delivery_ts,
                    stg.rate,
                    stg.tip_sum
                FROM stg.deliveries stg
                JOIN dds.dm_orders 
                    ON dm_orders.order_key = stg.order_id
                JOIN dds.dm_couriers 
                    ON dm_couriers.courier_id = stg.courier_id
                ON CONFLICT (order_id, courier_id) DO UPDATE SET
                    delivery_ts = EXCLUDED.delivery_ts,
                    rate = EXCLUDED.rate,
                    tip_sum = EXCLUDED.tip_sum
            """)
            
            result = conn.execute(query)
            log.info(f'Загружено {result.rowcount} доставок в fct_deliveries')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке fct_deliveries: {e}', exc_info=True)
        raise


def update_dm_orders_courier(
    dwh_conn_id: str,
    schema: str = 'dds'
) -> None:
    """
    Обновляет dm_orders — проставляет courier_id из доставок
    """
    log.info('Обновляем dm_orders — проставляем courier_id')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            query = text("""
                UPDATE dds.dm_orders
                SET courier_id = fct.courier_id
                FROM dds.fct_deliveries fct
                WHERE dm_orders.id = fct.order_id
                AND dm_orders.courier_id IS NULL
            """)
            
            result = conn.execute(query)
            log.info(f'Обновлено {result.rowcount} заказов с courier_id')
            
    except Exception as e:
        log.error(f'Ошибка при обновлении dm_orders: {e}', exc_info=True)
        raise

def load_dm_courier_ledger(
    dwh_conn_id: str,
    schema: str = 'cdm'
) -> None:
    """
    Загружает витрину dm_courier_ledger из DDS слоя
    """
    log.info('Начинаем загрузку dm_courier_ledger из DDS')
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        with engine.begin() as conn:
            log.info('Очищаем cdm.dm_courier_ledger')
            conn.execute(text('TRUNCATE TABLE cdm.dm_courier_ledger RESTART IDENTITY CASCADE'))
            
            insert_query = text("""
                WITH courier_monthly_stats AS (
                    SELECT 
                        c.courier_id,
                        c.courier_name,
                        EXTRACT(YEAR FROM t.ts)::int as settlement_year,
                        EXTRACT(MONTH FROM t.ts)::int as settlement_month,
                        COUNT(DISTINCT o.id) as orders_count,
                        COALESCE(SUM(fs.total_sum), 0) as orders_total_sum,
                        COALESCE(AVG(d.rate), 0) as rate_avg,
                        COALESCE(SUM(fs.total_sum), 0) * 0.25 as order_processing_fee,
                        COALESCE(SUM(d.tip_sum), 0) as courier_tips_sum
                    FROM dds.dm_couriers c
                    JOIN dds.fct_deliveries d ON c.id = d.courier_id
                    JOIN dds.dm_orders o ON d.order_id = o.id
                    JOIN dds.dm_timestamps t ON o.timestamp_id = t.id
                    JOIN dds.fct_product_sales fs ON o.id = fs.order_id
                    WHERE o.order_status = 'CLOSED'
                    GROUP BY 
                        c.courier_id,
                        c.courier_name,
                        EXTRACT(YEAR FROM t.ts),
                        EXTRACT(MONTH FROM t.ts)
                )
                INSERT INTO cdm.dm_courier_ledger (
                    courier_id,
                    courier_name,
                    settlement_year,
                    settlement_month,
                    orders_count,
                    orders_total_sum,
                    rate_avg,
                    order_processing_fee,
                    courier_order_sum,
                    courier_tips_sum,
                    courier_reward_sum
                )
                SELECT 
                    courier_id,
                    courier_name,
                    settlement_year,
                    settlement_month,
                    orders_count,
                    orders_total_sum,
                    rate_avg,
                    order_processing_fee,
                    GREATEST(
                        CASE 
                            WHEN rate_avg < 4 THEN orders_total_sum * 0.05
                            WHEN rate_avg < 4.5 THEN orders_total_sum * 0.07
                            WHEN rate_avg < 4.9 THEN orders_total_sum * 0.08
                            ELSE orders_total_sum * 0.10
                        END,
                        CASE 
                            WHEN rate_avg < 4 THEN 100 * orders_count
                            WHEN rate_avg < 4.5 THEN 150 * orders_count
                            WHEN rate_avg < 4.9 THEN 175 * orders_count
                            ELSE 200 * orders_count
                        END
                    ) as courier_order_sum,
                    courier_tips_sum,
                    GREATEST(
                        CASE 
                            WHEN rate_avg < 4 THEN orders_total_sum * 0.05
                            WHEN rate_avg < 4.5 THEN orders_total_sum * 0.07
                            WHEN rate_avg < 4.9 THEN orders_total_sum * 0.08
                            ELSE orders_total_sum * 0.10
                        END,
                        CASE 
                            WHEN rate_avg < 4 THEN 100 * orders_count
                            WHEN rate_avg < 4.5 THEN 150 * orders_count
                            WHEN rate_avg < 4.9 THEN 175 * orders_count
                            ELSE 200 * orders_count
                        END
                    ) + courier_tips_sum * 0.95 as courier_reward_sum
                FROM courier_monthly_stats
                ORDER BY 
                    settlement_year DESC,
                    settlement_month DESC,
                    courier_id
            """)
            
            result = conn.execute(insert_query)
            log.info(f'Вставлено {result.rowcount} записей в dm_courier_ledger')
            
    except Exception as e:
        log.error(f'Ошибка при загрузке dm_courier_ledger: {e}', exc_info=True)
        raise