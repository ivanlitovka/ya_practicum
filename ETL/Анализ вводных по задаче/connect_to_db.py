import psycopg2
import pandas as pd
import numpy as np

conn = psycopg2.connect(
host="postgres",
port=5432,
dbname="student",
user="student",
password="student-de"
)
# переменная conn создаёт подключение к БД
cur = conn.cursor()  

cur.close()
conn.close()