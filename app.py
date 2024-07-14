from flask import Flask, request, jsonify, abort, g
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

# Se crea función que conecta a la base de datos
def get_db_connection():
    conn = sqlite3.connect('iot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# Creación de tablas
def init_db():
    # Se crea tabla Admin
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Admin (
        Username STRING PRIMARY KEY,
        Password STRING NOT NULL
    )
    ''')

    # Se crea la tabla Company
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Company(
        ID INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        Company_name STRING NOT NULL,
        Company_api_key STRING NOT NULL
    )
    ''')
    
    # Se crea la tabla Location
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

    # Se crea la tabla Sensor
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

    # Se crea la tabla Sensor_Data
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Sensor_Data(
        ID INT PRIMARY KEY AUTOINCREMENT NOT NULL,
        sensor_id INT NOT NULL,
        data TEXT NOT NULL,
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGNKEY (sensor_id) REFERENCES Sensor(sensor_id))
    )
    ''')

    # Confirmar las transacciones realizadas
    conn.commit()

    # Cierra la conexión a la base de datos
    conn.close()

# Inicializa la base de datos.
init_db()


# Se crea un decorador que se encarga de validar el company_api_key
def require_company_api_key(f):
    def decorator(*args, **kwargs):
        # Obtiene el company_api_key de los parámetros de la petición.
        company_api_key = request.args.get('company_api_key')
        # Si no es válido el api key, aborta la petición con un error HTTP 400
        if not company_api_key:
            abort(400, 'company_api_key is required')
        
        # Si el api key es válido, busca la compañía a la que corresponde
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT ID FROM Company WHERE company_api_key = ?', (company_api_key,))
        company = cur.fetchone()
        conn.close()
        
        # Si no la encuentra, aborta la petición con error HTTP 401
        if not company:
            abort(401, 'Invalid company_api_key')
        
        g.company_id = company['ID']
        # Ejecuta la función original si el API key es válido
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

# Se crea validador del sensor_api_key
def require_sensor_api_key(f):
    def decorator(*args, **kwargs):
        sensor_api_key = request.args.get('company_api_key')

        if not sensor_api_key:
            abort(400, 'sensor_api_key is required')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT sensor_id FROM Sensor WHERE sensor_api_key = ?', (sensor_api_key,))
        sensor = cur.fetchone()
        conn.close()

        if not sensor:
            abort(401, 'Invalid sensor_api_key')

        g.sensor_id = sensor['sensor_id']
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator


# TABLA LOCATION

# Muestra todo de tabla Location que pertenezcan a la compañía validada por api key
@app.route('/api/v1/location', methods=['GET'])
# Valida el api key
@require_company_api_key
def get_locations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM Location')
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Muestra uno de tabla Location, por nombre 
@app.route('/api/v1/location/<location_name>', methods=['GET'])
@require_company_api_key
def get_location(location_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id))
    location = cur.fetchone()
    conn.close()
    if not location:
        abort(404, 'Location not found')
    return jsonify(dict(location)), 200

# Edita en tabla Location, por nombre
@app.route('/api/v1/location/<location_name>', methods=['PUT'])
@require_company_api_key
def update_location(location_name):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Obtener la ubicación actual
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id))
    location = cur.fetchone()
    if not location:
        conn.close()
        abort(404, 'Location not found')

    # Actualizar la ubicación
    location_name = request.json.get('location_name')
    location_country = request.json.get('location_country')
    location_city = request.json.get('location_city')
    location_meta = request.json.get('location_meta')
    
    cur.execute('''
        UPDATE Location 
        SET location_name = ?, location_country = ?, location_city = ?, location_meta = ?
        WHERE location_name = ? AND company_id = ?
    ''', (location_name, location_country, location_city, location_meta, location_name, g.company_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated successfully'}), 200

# Elimina en tabla Location
@app.route('/api/v1/location/<location_name>', methods=['DELETE'])
@require_company_api_key
def delete_location(location_name):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verificar si la ubicación existe
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id))
    location = cur.fetchone()
    if not location:
        conn.close()
        abort(404, 'Location not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200

# TABLA SENSOR

# Muestra todo de tabla Sensor que correspondan a las ubicaciones de la compañía validada por api key
@app.route('/api/v1/sensor', methods=['GET'])
# Valida el api key
@require_company_api_key
def get_sensors():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?)', (g.company_id,))    
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Muestra uno de tabla Sensor que se encuentre en las ubicaciones de la compañía validada por api key
@app.route('/api/v1/sensor/<int:sensor_id>', methods=['GET'])
@require_company_api_key
def get_sensor(sensor_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', (sensor_id, g.company_id))
    row = cur.fetchone()
    conn.close()
    if not row:
        abort(404, 'Sensor not found')
    return jsonify(dict(row)), 200

# Edita en tabla Sensor
@app.route('/api/v1/sensor/<int:sensor_id>', methods=['PUT'])
@require_company_api_key
def update_sensor(sensor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener el sensor
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', (sensor_id, g.company_id))
    sensor = cur.fetchone()
    if not sensor:
        conn.close()
        abort(404, 'Sensor not found')

    # Actualizar sensor
    location_id = request.json.get('location_id')
    sensor_name = request.json.get('sensor_name')
    sensor_category = request.json.get('sensor_category')
    sensor_meta = request.json.get('sensor_meta')
    
    cur.execute('UPDATE Sensor SET location_id = ?, sensor_name = ?, sensor_category = ?, sensor_meta = ? WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', 
                (location_id, sensor_name, sensor_category, sensor_meta, sensor_id, g.company_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated successfully'}), 200

# Elimina en tabla Sensor
@app.route('/api/v1/sensor/<int:sensor_id>', methods=['DELETE'])
@require_company_api_key
def delete_sensor(sensor_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verificar si el sensor existe
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?', (sensor_id, g.company_id))
    sensor = cur.fetchone()
    if not sensor:
        conn.close()
        abort(404, 'Sensor not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?', (sensor_id, g.company_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200

# TABLA SENSOR_DATA

# Muestra todo de tabla Sensor_Data que correspondan a los sensores de las ubicaciones de la compañía validada por api key
@app.route('/api/v1/sensor_data', methods=['GET'])
# Valida el api key
@require_company_api_key
def get_sensors_data():
    from_time = request.args.get('from')
    to_time = request.args.get('to')
    sensor_ids = request.args.getlist('sensor_id')

    if not from_time or not to_time or not sensor_ids:
        abort(400, 'Missing required parameters')

    # Construir y ejecutar la consulta de sensor_data
    query = 'SELECT * FROM Sensor_Data WHERE sensor_id IN ({seq}) AND tiempo BETWEEN ? AND ?'
    query = query.format(seq=','.join(['?'] * len(sensor_ids)))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, sensor_ids + [from_time, to_time])
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Muestra uno de tabla Sensor_Data que se encuentre en el sensor de las ubicaciones de la compañía validada por api key
#@app.route('/api/v1/sensor_data/<int:ID>', methods=['GET'])
#@require_company_api_key
#def get_sensor_data(ID):
#    conn = get_db_connection()
#    cur = conn.cursor()
#    cur.execute('SELECT * FROM Sensor_Data WHERE ID = ? AND sensor_id = AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', (sensor_id, g.company_id))
#    row = cur.fetchone()
#    conn.close()
#    if not row:
#        abort(404, 'Sensor not found')
#    return jsonify(dict(row)), 200


# Edita en tabla Sensor_Data
@app.route('/api/v1/sensor_data/<int:ID>', methods=['PUT'])
@require_company_api_key
@require_sensor_api_key #esto no se si va
def update_sensor_data(ID):
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener el sensor
    cur.execute('SELECT * FROM Sensor WHERE ID = ? AND sensor_id = ?)', (ID, g.sensor_id))
    sensor = cur.fetchone()
    if not sensor:
        conn.close()
        abort(404, 'Sensor not found')

    # Actualizar sensor_data
    sensor_id = request.json.get('sensor_id')
    data = request.json.get('data')
    time = request.json.get('time')
    
    cur.execute('UPDATE Sensor_Data SET sensor_id = ?, data = ?, time = ? WHERE ID = ? AND sensor_id = ?)', 
                (sensor_id, data, time, ID, g.sensor_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated successfully'}), 200

# Elimina en tabla Sensor_Data
@app.route('/api/v1/sensor_data/<int:ID>', methods=['DELETE'])
@require_company_api_key
@require_sensor_api_key
def delete_sensor_data(ID):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verificar si el sensor_data existe
    cur.execute('SELECT * FROM Sensor_Data WHERE ID = ? AND sensor_id = ?', (ID, g.sensor_id))
    sensor_data = cur.fetchone()
    if not sensor_data:
        conn.close()
        abort(404, 'Sensor data not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Sensor_Data WHERE ID = ? AND sensor_id = ?', (ID, g.sensor_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200
