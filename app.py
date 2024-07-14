from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('iot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Admin (
        Username STRING PRIMARY KEY,
        Password STRING NOT NULL
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS Company(
        ID INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        Company_name STRING NOT NULL,
        Company_api_key STRING NOT NULL
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS Location(
        ID INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        company_id INT NOT NULL,
        location_name STRING NOT NULL,
        location_country STRING NOT NULL,
        location_city STRING NOT NULL,
        location_meta STRING NOT NULL,
        FOREIGNKEY (company_id) REFERENCES Company(ID)
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS Sensor(
        location_id INT NOT NULL,
        sensor_id INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        sensor_name STRING NOT NULL,
        sensor_category STRING NOT NULL,
        sensor_meta STRING NOT NULL,
        sensor_api_key STRING NOT NULL,
        FOREIGNKEY (location_id) REFERENCES Location(ID)
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS Sensor_Data(
        ID INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        sensor_id INT NOT NULL,
        tiempo DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGNKEy (sensor_id) REFERENCES Sensor(sensor_id))
    )
    ''')



    conn.commit()
    conn.close()

init_db()