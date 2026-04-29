import json
import requests
import time
import pandas as pd
import psycopg2


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
        r = requests.get(url + method_url + '?task_id=' + task_id, headers=headers)
        response_dict = json.loads(r.content)
        s3_paths = response_dict['data']['s3_path']
        return s3_paths


def load_data_to_stage(s3_paths):
    for key, value in s3_paths.items():
        if key == 'customer_research':
            load_csv = pd.read_csv(value, index_col=False)
            insert_s = 'INSERT INTO stage.customer_research (date_id, category_id, geo_id, sales_qty, sales_amt) VALUES ({s_val})'
        elif key == 'user_activity_log':
            load_csv = pd.read_csv(value, index_col=False, usecols=['date_time', 'action_id', 'customer_id', 'quantity'])
            insert_s = 'INSERT INTO stage.user_activity_log (date_time, action_id, customer_id, quantity) VALUES ({s_val})'
        elif key == 'user_order_log':
            load_csv = pd.read_csv(value, index_col=False, usecols=['date_time', 'city_id', 'city_name', 'customer_id', 'first_name', 'last_name', 'item_id', 'item_name', 'quantity', 'payment_amount'])
            insert_s = 'INSERT INTO stage.user_order_log (date_time, city_id, city_name, customer_id, first_name, last_name, item_id, item_name, quantity, payment_amount) VALUES ({s_val})'
        else:
            print(f'Файл {key}.csv пропущен')
            continue
        print(f'Загрузка {key}.csv')
        step = int(load_csv.shape[0] / 100)
        i = 0
        # for index, row in load_csv.iterrows():
        #     s_val = str(tuple(row))[1:-1]  # преобразуем строку в кортеж, убираем скобки
        #     cur.execute(insert_s.replace('{s_val}', s_val))
        #     conn.commit()

        while i < load_csv.shape[0]:  # исправлено: < вместо <=
            print(i, end='\r')

            # Определяем границы среза, чтобы не выйти за пределы DataFrame
            end_idx = min(i + step, load_csv.shape[0])
            data_slice = load_csv.iloc[i:end_idx]  # используем iloc вместо loc для позиционной индексации

            # Формируем список строк-кортежей
            tuples_list = [str(tuple(row)) for row in data_slice.values]

            # Объединяем кортежи через запятую — получаем корректный синтаксис VALUES (..), (..)
            s_val = ', '.join(tuples_list)

            cur.execute(insert_s.replace('{s_val}', s_val))
            conn.commit()

            i = end_idx  # переходим к следующей порции


task_id = get_report('/generate_report')
time.sleep(60)
s3_paths = get_report('/get_report', task_id)

try:
    conn = psycopg2.connect(
        host="localhost",
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
