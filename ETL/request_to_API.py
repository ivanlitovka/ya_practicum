import json
import requests
import time

'''
generate_report_response = requests.post(
    "https://d5dg1j9kt695d30blp03.apigw.yandexcloud.net/generate_report",  # точка входа
    headers={
        "X-API-KEY": "5f55e6c0-e9e5-4a9c-b313-63c01fc31460",  # ключ API
        "X-Nickname": "ewanlitovka",  # авторизационные данные
        "X-Cohort": "16"  # авторизационные данные
    }
).json()

task_id = generate_report_response["task_id"]

time.sleep(60)

get_report_response = requests.get(
    f"https://d5dg1j9kt695d30blp03.apigw.yandexcloud.net/get_report?task_id={task_id}",
    headers={
        "X-API-KEY": "5f55e6c0-e9e5-4a9c-b313-63c01fc31460",
        "X-Nickname": "ewanlitovka",
        "X-Cohort": "16"
    }
).json()
report_id = get_report_response['data']['report_id']
print(report_id)
'''

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
print(response_dict)
task_id = response_dict['task_id']
time.sleep(60)
method_url = f'/get_report?task_id={task_id}'
r = requests.get(url + method_url, headers=headers)
response_dict = json.loads(r.content)
print(response_dict)
