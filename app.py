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
    CREATE TABLE IF NOT EXISTS iot_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        data TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()