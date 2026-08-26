"""
DAG для загрузки данных из API курьерской службы в STG слой
"""
from airflow.decorators import dag, task
from airflow.models import Variable
import logging
import pendulum
import requests
import json

from my_lib import create_postgres_engine

log = logging.getLogger(__name__)

# Конфигурация API
API_URL = 'https://d5d04q7d963eapoepsqr.apigw.yandexcloud.net'
NICKNAME = 'ewanlitovka'
COHORT = '16'
API_KEY = '25c27781-8fde-4b30-a22e-524044a7580f'


def get_headers():
    """Возвращает заголовки для запросов к API"""
    return {
        'X-Nickname': NICKNAME,
        'X-Cohort': COHORT,
        'X-API-KEY': API_KEY
    }


def fetch_all_pages(endpoint: str, params: dict = None) -> list:
    """
    Загружает все данные из API с пагинацией
    """
    all_data = []
    offset = 0
    limit = 50
    
    while True:
        params['limit'] = limit
        params['offset'] = offset
        
        url = f"{API_URL}/{endpoint}"
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()
        
        data = response.json()
        if not data:
            break
            
        all_data.extend(data)
        
        if len(data) < limit:
            break
            
        offset += limit
    
    log.info(f'Загружено {len(all_data)} записей из {endpoint}')
    return all_data


@task(task_id='load_couriers')
def load_couriers():
    """Загрузка курьеров из API в stg.couriers"""
    log.info('Начинаем загрузку курьеров из API')
    
    # Получаем данные из API
    couriers = fetch_all_pages('couriers', {'sort_field': '_id', 'sort_direction': 'asc'})
    
    if not couriers:
        log.warning('Нет данных о курьерах')
        return
    
    engine = create_postgres_engine('PG_WAREHOUSE_CONNECTION')
    
    with engine.begin() as conn:
        # Очищаем таблицу
        conn.execute('TRUNCATE TABLE stg.couriers RESTART IDENTITY CASCADE')
        
        # Вставляем данные
        for courier in couriers:
            conn.execute("""
                INSERT INTO stg.couriers (courier_id, courier_name)
                VALUES (%s, %s)
                ON CONFLICT (courier_id) DO UPDATE SET
                    courier_name = EXCLUDED.courier_name
            """, (courier['_id'], courier['name']))
    
    log.info(f'Загружено {len(couriers)} курьеров')


@task(task_id='load_deliveries')
def load_deliveries():
    """Загрузка доставок из API в stg.deliveries"""
    log.info('Начинаем загрузку доставок из API')
    
    # Загружаем за последние 7 дней
    from_date = pendulum.now('UTC').subtract(days=7).format('YYYY-MM-DD HH:mm:ss')
    to_date = pendulum.now('UTC').format('YYYY-MM-DD HH:mm:ss')
    
    params = {
        'from': from_date,
        'to': to_date,
        'sort_field': '_id',
        'sort_direction': 'asc'
    }
    
    deliveries = fetch_all_pages('deliveries', params)
    
    if not deliveries:
        log.warning('Нет данных о доставках')
        return
    
    engine = create_postgres_engine('PG_WAREHOUSE_CONNECTION')
    
    with engine.begin() as conn:
        # Очищаем таблицу
        conn.execute('TRUNCATE TABLE stg.deliveries RESTART IDENTITY CASCADE')
        
        # Вставляем данные
        for d in deliveries:
            conn.execute("""
                INSERT INTO stg.deliveries (
                    order_id, order_ts, delivery_id, courier_id,
                    address, delivery_ts, rate, sum, tip_sum
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (delivery_id) DO UPDATE SET
                    order_id = EXCLUDED.order_id,
                    order_ts = EXCLUDED.order_ts,
                    courier_id = EXCLUDED.courier_id,
                    address = EXCLUDED.address,
                    delivery_ts = EXCLUDED.delivery_ts,
                    rate = EXCLUDED.rate,
                    sum = EXCLUDED.sum,
                    tip_sum = EXCLUDED.tip_sum
            """, (
                d['order_id'],
                d['order_ts'],
                d['delivery_id'],
                d['courier_id'],
                d['address'],
                d['delivery_ts'],
                d['rate'],
                d['sum'],
                d['tip_sum']
            ))
    
    log.info(f'Загружено {len(deliveries)} доставок')


@dag(
    schedule_interval='0 */6 * * *',  # Каждые 6 часов
    start_date=pendulum.datetime(2026, 8, 1, tz='UTC'),
    catchup=False,
    tags=['sprint5', 'api', 'stg'],
    is_paused_upon_creation=False,
    default_args={
        'owner': 'airflow',
        'retries': 2,
        'retry_delay': pendulum.duration(minutes=5),
    }
)
def load_api_to_stg():
    """Загрузка данных из API курьерской службы в STG"""
    couriers_task = load_couriers()
    deliveries_task = load_deliveries()
    
    # Задачи могут выполняться параллельно
    [couriers_task, deliveries_task]


dag = load_api_to_stg()