import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    conn = psycopg2.connect(dbname="postgres", user="postgres", host="localhost", port=5432)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE leadhunter_db;")
    cursor.close()
    conn.close()
    print("Database created successfully")
except Exception as e:
    print("Error:", e)
