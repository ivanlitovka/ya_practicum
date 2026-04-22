import json
import requests
import time
import pandas as pd
import os


url = 'https://d5dg1j9kt695d30blp03.apigw.yandexcloud.net'
nickname = "ewanlitovka"
cohort = "16"
headers = {
    "X-API-KEY": "5f55e6c0-e9e5-4a9c-b313-63c01fc31460",
    "X-Nickname": nickname,
    "X-Cohort": cohort
}

method_url = '/generate_report'
r = requests.post(url + method_url, headers=headers)
response_dict = json.loads(r.content)
task_id = response_dict['task_id']
time.sleep(60)
# После ожидания получаем report_id и ссылки на файлы в json
method_url = f'/get_report?task_id={task_id}'
r = requests.get(url + method_url, headers=headers)
response_dict = json.loads(r.content)
# print(response_dict)
s3_paths = response_dict['data']['s3_path']

# Превращаем в список значений (самих URL)
links_list = list(s3_paths.values())
os.makedirs('./stage', exist_ok=True)
# print(links_list)
for link in links_list:
    print(link)
    print(link.split('/')[-1])
    df_order_log = pd.read_csv(link)
    df_order_log.to_csv(f'./stage/{link.split("/")[-1]}')
