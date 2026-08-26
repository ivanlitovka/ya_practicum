"""
Библиотека для работы с MongoDB в Airflow
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dateutil import parser

from airflow.models import Variable
from pymongo import MongoClient
from pymongo.database import Database
import pandas as pd
from sqlalchemy import text
from bson import json_util

from my_lib import create_postgres_engine, load_data_to_dwh

log = logging.getLogger(__name__)


def get_mongo_client() -> MongoClient:
    """
    Создает клиент для подключения к MongoDB из переменных Airflow
    
    Returns:
        MongoClient: Клиент MongoDB
    """
    # Получаем параметры из переменных Airflow
    host = Variable.get('MONGO_DB_HOST')
    user = Variable.get('MONGO_DB_USER')
    password = Variable.get('MONGO_DB_PASSWORD')
    replica_set = Variable.get('MONGO_DB_REPLICA_SET')
    database = Variable.get('MONGO_DB_DATABASE_NAME')
    certificate_path = Variable.get('MONGO_DB_CERTIFICATE_PATH')
    
    # Формируем строку подключения
    uri = f"mongodb://{user}:{password}@{host}/{database}"
    
    # Добавляем параметры
    uri += f"?replicaSet={replica_set}"
    uri += "&ssl=true"
    uri += f"&tlsCAFile={certificate_path}"
    uri += "&retryWrites=false"
    uri += "&directConnection=true"
    
    log.info(f'Создаем подключение к MongoDB: {host}')
    
    try:
        client = MongoClient(uri)
        # Проверяем подключение
        client.admin.command('ping')
        log.info('Подключение к MongoDB успешно')
        return client
    except Exception as e:
        log.error(f'Ошибка подключения к MongoDB: {e}', exc_info=True)
        raise


def get_mongo_database() -> Database:
    """
    Получает базу данных MongoDB
    
    Returns:
        Database: База данных MongoDB
    """
    client = get_mongo_client()
    db_name = Variable.get('MONGO_DB_DATABASE_NAME')
    return client[db_name]


def extract_mongo_collection(
    collection_name: str,
    query: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    sort_field: Optional[str] = None,
    sort_order: int = 1
) -> List[Dict[str, Any]]:
    """
    Извлекает данные из MongoDB коллекции
    
    Args:
        collection_name: Имя коллекции
        query: Фильтр для запроса (по умолчанию все документы)
        limit: Ограничение количества документов
        sort_field: Поле для сортировки
        sort_order: 1 - по возрастанию, -1 - по убыванию
    
    Returns:
        List[Dict]: Список документов
    """
    log.info(f'Извлекаем данные из коллекции {collection_name}')
    
    try:
        db = get_mongo_database()
        collection = db[collection_name]
        
        # Выполняем запрос
        cursor = collection.find(query or {})
        
        # Сортировка
        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)
        
        # Лимит
        if limit:
            cursor = cursor.limit(limit)
        
        # Преобразуем в список
        documents = list(cursor)
        
        log.info(f'Извлечено {len(documents)} документов из коллекции {collection_name}')
        return documents
        
    except Exception as e:
        log.error(f'Ошибка при извлечении данных из {collection_name}: {e}', exc_info=True)
        raise


def normalize_datetime(dt: datetime) -> datetime:
    """
    Приводит datetime к единому формату (UTC, без часового пояса)
    
    Args:
        dt: datetime объект
    
    Returns:
        datetime: нормализованный datetime (UTC, naive)
    """
    if dt is None:
        return None
    
    # Если есть часовой пояс - конвертируем в UTC и убираем его
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    
    return dt


def get_last_loaded_ts(
    dwh_conn_id: str,
    workflow_key: str,
    schema: str = 'stg',
    default: str = '1970-01-01T00:00:00.000Z'
) -> datetime:
    """
    Получает последнюю загруженную дату из таблицы srv_wf_settings
    
    Args:
        dwh_conn_id: ID соединения с DWH
        workflow_key: Ключ задачи
        schema: Схема таблицы
        default: Значение по умолчанию
    
    Returns:
        datetime: Последняя загруженная дата как datetime объект (UTC, naive)
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
                    # Парсим строку в datetime и нормализуем
                    try:
                        dt = parser.parse(last_ts_str)
                        return normalize_datetime(dt)
                    except:
                        log.warning(f'Не удалось распарсить {last_ts_str}, используем default')
                        return normalize_datetime(parser.parse(default))
                else:
                    log.info(f'Запись найдена, но нет last_loaded_ts, используем default')
                    return normalize_datetime(parser.parse(default))
            else:
                log.info(f'Запись не найдена, используем default')
                return normalize_datetime(parser.parse(default))
    except Exception as e:
        log.error(f'Ошибка при получении last_loaded_ts: {e}', exc_info=True)
        raise


def save_loaded_state_ts(
    dwh_conn_id: str,
    workflow_key: str,
    last_loaded_ts: datetime,
    schema: str = 'stg'
) -> None:
    """
    Сохраняет состояние загрузки в таблицу srv_wf_settings
    
    Args:
        dwh_conn_id: ID соединения с DWH
        workflow_key: Ключ задачи
        last_loaded_ts: Последняя загруженная дата как datetime объект
        schema: Схема таблицы
    """
    # Нормализуем datetime перед сохранением
    normalized_ts = normalize_datetime(last_loaded_ts)
    last_loaded_ts_str = normalized_ts.isoformat()
    
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


def save_to_stg_table(
    dwh_conn_id: str,
    table_name: str,
    schema: str,
    object_id: str,
    object_value: str,
    update_ts: datetime
) -> None:
    """
    Сохраняет один документ в staging таблицу с upsert логикой
    
    Args:
        dwh_conn_id: ID соединения с DWH
        table_name: Название таблицы
        schema: Схема
        object_id: ID объекта (из MongoDB _id)
        object_value: JSON представление документа
        update_ts: Время обновления как datetime объект
    """
    # Нормализуем datetime перед сохранением в PostgreSQL
    normalized_ts = normalize_datetime(update_ts)
    
    try:
        engine = create_postgres_engine(dwh_conn_id)
        
        # Upsert: обновляем если существует, иначе вставляем
        query = text(f"""
            INSERT INTO {schema}.{table_name} (object_id, object_value, update_ts)
            VALUES (:object_id, :object_value, :update_ts)
            ON CONFLICT (object_id) 
            DO UPDATE SET 
                object_value = EXCLUDED.object_value,
                update_ts = EXCLUDED.update_ts
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {
                'object_id': object_id,
                'object_value': object_value,
                'update_ts': normalized_ts
            })
            
    except Exception as e:
        log.error(f'Ошибка при сохранении документа {object_id} в {schema}.{table_name}: {e}', exc_info=True)
        raise


def extract_load_mongo_collection(
    collection_name: str,
    dwh_conn_id: str,
    dwh_table: str,
    workflow_key: str,
    dwh_schema: str = 'stg',
    batch_size: int = 1000,
    date_field: str = 'update_ts'
) -> None:
    """
    Основная функция для ETL из MongoDB в DWH
    
    Args:
        collection_name: Имя коллекции в MongoDB
        dwh_conn_id: ID соединения с DWH
        dwh_table: Название таблицы в DWH
        workflow_key: Ключ для хранения состояния
        dwh_schema: Схема в DWH
        batch_size: Размер батча для загрузки
        date_field: Поле с датой обновления
    """
    log.info(f'Начинаем загрузку {collection_name} -> {dwh_schema}.{dwh_table}')
    
    # 1. Получаем последнюю загруженную дату как datetime объект (UTC, naive)
    last_ts = get_last_loaded_ts(
        dwh_conn_id=dwh_conn_id,
        workflow_key=workflow_key,
        schema=dwh_schema
    )
    log.info(f'Последняя загруженная дата: {last_ts}')
    
    # 2. Формируем запрос для извлечения новых данных
    query = {
        date_field: {'$gt': last_ts}
    }
    log.info(f'Запрос к MongoDB: {query}')
    
    # 3. Извлекаем данные из MongoDB с сортировкой и лимитом
    documents = extract_mongo_collection(
        collection_name=collection_name,
        query=query,
        limit=batch_size,
        sort_field=date_field,
        sort_order=1
    )
    
    if not documents:
        log.info(f'Нет новых данных в коллекции {collection_name}')
        return
    
    log.info(f'Извлечено {len(documents)} новых документов')
    
    # 4. Обрабатываем и сохраняем каждый документ
    max_ts = last_ts
    
    for doc in documents:
        # Извлекаем _id как строку
        object_id = str(doc.get('_id', ''))
        
        # Извлекаем update_ts и нормализуем
        update_ts = doc.get(date_field)
        
        if not update_ts:
            log.warning(f'Документ {object_id} не содержит {date_field}, пропускаем')
            continue
        
        # Нормализуем datetime (приводим к UTC, убираем часовой пояс)
        normalized_update_ts = normalize_datetime(update_ts)
        
        # Преобразуем весь документ в JSON строку
        object_value = json_util.dumps(doc)
        
        # Сохраняем в DWH
        save_to_stg_table(
            dwh_conn_id=dwh_conn_id,
            table_name=dwh_table,
            schema=dwh_schema,
            object_id=object_id,
            object_value=object_value,
            update_ts=normalized_update_ts
        )
        
        # Обновляем максимальную дату (сравниваем нормализованные datetime)
        if normalized_update_ts > max_ts:
            max_ts = normalized_update_ts
    
    # 5. Сохраняем состояние
    if max_ts > last_ts:
        save_loaded_state_ts(
            dwh_conn_id=dwh_conn_id,
            workflow_key=workflow_key,
            last_loaded_ts=max_ts,
            schema=dwh_schema
        )
        log.info(f'Сохранили состояние: last_loaded_ts = {max_ts.isoformat()}')
    else:
        log.info('Состояние не изменилось')
    
    log.info(f'Загрузка {collection_name} завершена. Загружено {len(documents)} документов')