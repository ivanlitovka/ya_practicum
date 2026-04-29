import json
import requests
import time
import pandas as pd
import psycopg2

'''
# Этот блок не секьюрный, но на макОС какая-то проблема с сертификатами 
# во время загрузки csv  в pandas, сделал так, возиться с сертификатами было лень.
import ssl
import urllib.request

# Отключаем проверку SSL для urllib
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


# Применяем к urllib
urllib.request.install_opener(
    urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context)
    )
)
'''


def get_report(method_url, task_id=None):
    url = 'https://d5dg1j9kt695d30blp03.apigw.yandexcloud.net'
    nickname = "ewanlitovka"
    cohort = "16"
    headers = {
        "X-API-KEY": "5f55e6c0-e9e5-4a9c-b313-63c01fc31460",
        "X-Nickname": nickname,
        "X-Cohort": cohort
    }

    if method_url == '/generate_report':
        r = requests.post(url + method_url, headers=headers)
        response_dict = json.loads(r.content)
        task_id = response_dict['task_id']
        return task_id
    elif method_url == '/get_report' and task_id != None:
        r = requests.get(url + method_url + '?task_id=' +
                         task_id, headers=headers)
        response_dict = json.loads(r.content)
        s3_paths = response_dict['data']['s3_path']
        return s3_paths


def load_data_to_stage(s3_paths):
    for key, value in s3_paths.items():
        if key == 'customer_research':
            load_csv = pd.read_csv(value, index_col=False)
            columns = ['date_id', 'category_id',
                       'geo_id', 'sales_qty', 'sales_amt']
            table = 'stage.customer_research'
        elif key == 'user_activity_log':
            load_csv = pd.read_csv(value, index_col=False, usecols=[
                'date_time', 'action_id', 'customer_id', 'quantity'])
            columns = ['date_time', 'action_id', 'customer_id', 'quantity']
            table = 'stage.user_activity_log'
        elif key == 'user_order_log':
            load_csv = pd.read_csv(value, index_col=False, usecols=[
                'date_time', 'city_id', 'city_name', 'customer_id', 'first_name', 'last_name', 'item_id', 'item_name', 'quantity', 'payment_amount'])
            columns = ['date_time', 'city_id', 'city_name', 'customer_id', 'first_name',
                       'last_name', 'item_id', 'item_name', 'quantity', 'payment_amount']
            table = 'stage.user_order_log'
        else:
            print(f'Файл {key}.csv пропущен')
            continue

        print(f'Загрузка {key}.csv')
        step = 1000  # Оптимальный размер пачки

        for i in range(0, len(load_csv), step):
            data_slice = load_csv.iloc[i:i + step]
            # Преобразуем DataFrame в список кортежей
            data_tuples = [tuple(x) for x in data_slice[columns].values]

            # Используем executemany с плейсхолдерами %s — безопасно и корректно
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"

            try:
                cur.executemany(insert_query, data_tuples)
                conn.commit()
                print(
                    f"Загружено {len(data_tuples)} строк (порция {i // step + 1})")
            except Exception as e:
                print(f"Ошибка при загрузке порции: {e}")
                conn.rollback()
                raise


task_id = get_report('/generate_report')
time.sleep(60)
s3_paths = get_report('/get_report', task_id)

try:
    conn = psycopg2.connect(
        host="111.88.145.161",
        port=15432,
        dbname="student",
        user="student",
        password="student-de"
    )
    print('Успешное подключение к базе данных')
except psycopg2.OperationalError as e:
    print(f'Ошибка подключения к БД: {e}')
    exit(1)
# переменная conn создаёт подключение к БД
cur = conn.cursor()
load_data_to_stage(s3_paths)

cur.close()
conn.close()
