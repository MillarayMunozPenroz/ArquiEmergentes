from flask import Flask, request, jsonify, abort, g
import sqlite3
import uuid
import logging
from logging import FileHandler, Formatter


app = Flask(__name__)

# Se crea función que conecta a la base de datos
def get_db_connection():
    conn = sqlite3.connect('iot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# Creación de tablas
def init_db():
    try:
        # Se crea tabla Admin
        conn = get_db_connection()
        print("Initializing database...")
        conn.execute('''
        CREATE TABLE IF NOT EXISTS Admin (
            Username STRING PRIMARY KEY,
            Password STRING NOT NULL
        )
        ''')
        print("Admin table created.")

        # Se crea la tabla Company
        conn.execute('''
        CREATE TABLE IF NOT EXISTS Company(
            ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            Company_name STRING NOT NULL,
            Company_api_key STRING NOT NULL
        )
        ''')
        print("Company table created.")
        
        # Se crea la tabla Location
        conn.execute('''
        CREATE TABLE IF NOT EXISTS Location(
            ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            company_id INTEGER NOT NULL,
            location_name STRING NOT NULL,
            location_country STRING NOT NULL,
            location_city STRING NOT NULL,
            location_meta STRING NOT NULL,
            FOREIGNKEY company_id REFERENCES Company(ID)
        )
        ''')
        print("Location table created.")

        # Se crea la tabla Sensor
        conn.execute('''
        CREATE TABLE IF NOT EXISTS Sensor(
            location_id INTEGER NOT NULL,
            sensor_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            sensor_name STRING NOT NULL,
            sensor_category STRING NOT NULL,
            sensor_meta STRING NOT NULL,
            sensor_api_key STRING NOT NULL,
            FOREIGNKEY location_id REFERENCES Location(ID)
        )
        ''')
        print("Sensor table created.")

        # Se crea la tabla Sensor_Data
        conn.execute('''
        CREATE TABLE IF NOT EXISTS Sensor_Data(
            ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            sensor_id INTEGER NOT NULL,
            data STRING NOT NULL,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGNKEY sensor_id REFERENCES Sensor(sensor_id)
        )
        ''')
        print("Sensor_Data table created.")

        # Confirmar las transacciones realizadas
        conn.commit()
        print("Database initialized successfully.")

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise  # Levantar la excepción para identificar problemas durante la inicialización
    finally:
        # Cierra la conexión a la base de datos
        conn.close()

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
        cur.execute('SELECT ID FROM Company WHERE company_api_key = ?', (company_api_key))
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
        cur.execute('SELECT sensor_id FROM Sensor WHERE sensor_api_key = ?', (sensor_api_key))
        sensor = cur.fetchone()
        conn.close()

        if not sensor:
            abort(401, 'Invalid sensor_api_key')

        g.sensor_id = sensor['sensor_id']
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

# Se crea un decorador que se encarga de validar el Admin
def require_admin(f):
    def decorator(*args, **kwargs):
        username = request.headers.get('Username')
        password = request.headers.get('Password')
        
        if not username or not password:
            abort(401, 'Admin credentials are required')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Admin WHERE Username = ? AND Password = ?', (username, password))
        admin = cur.fetchone()
        conn.close()
        
        if not admin:
            abort(403, 'Invalid admin credentials')
        
        g.admin = admin['Username']
        
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

# Creador de api key para la creación de compañías y sensores
def generate_api_key():
    return str(uuid.uuid4())

# Crear Admin
@app.route('/api/v1/crea_admin', methods=['POST'])
def create_admin():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Obtener información para crear al admin
        username = request.json['Username']
        password = request.json['Password']
    
        cur.execute('INSERT INTO Admin (Username, Password) VALUES (?, ?)', (username, password))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'message': 'Successfully created'}), 201

# TABLA Company

# Admin crea Company
@app.route('/api/v1/company', methods=['POST'])
@require_admin
def create_company():
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener información para crear la compañía y agregarla a la tabla
    company_name = request.json['Company_name']
    company_api_key = generate_api_key()

    cur.execute('INSERT INTO Company(Company_name, Company_api_key) VALUES(?, ?)', (company_name, company_api_key))
    conn.commit()
    company_id = cur.lastrowid
    conn.close()

    return jsonify({'company_id': company_id, 'company_api_key': company_api_key,  'message': 'Successfully created'}), 201

# Muestra todo de tabla Company que pertenezcan al admin validado por credenciales
@app.route('/api/v1/company', methods=['GET'])
# Valida el admin
@require_admin
def get_companys():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Company')
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# TABLA LOCATION

# Admin crea Ubicación
@app.route('/api/v1/location', methods=['POST'])
@require_admin
def create_location():
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtiene las variables
    company_id = request.json['company_id']
    location_name = request.json['location_name']
    location_country = request.json['location_country']
    location_city = request.json['location_city']
    location_meta = request.json['location_meta']
    
    cur.execute('INSERT INTO Location(company_id, location_name, location_country, location_city, location_meta) VALUES (?, ?, ?, ?, ?)', 
                (company_id, location_name, location_country, location_city, location_meta))
    conn.commit()
    location_id = cur.lastrowid
    conn.close()
    
    return jsonify({'location_id': location_id, 'message': 'Successfully created'}), 201

# Muestra todo de tabla Location que pertenezcan a la compañía validada por api key
@app.route('/api/v1/location', methods=['GET'])
# Valida el api key
@require_company_api_key
def get_locations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Location WHERE company_id = ?', (g.company_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Muestra uno de tabla Location, por nombre 
@app.route('/api/v1/location/<location_name>', methods=['GET'])
@require_company_api_key
def get_location(location_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id,))
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
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id,))
    location = cur.fetchone()
    if not location:
        conn.close()
        abort(404, 'Location not found')

    # Actualizar la ubicación
    location_name = request.json('location_name')
    location_country = request.json('location_country')
    location_city = request.json('location_city')
    location_meta = request.json('location_meta')
    
    cur.execute('''
        UPDATE Location 
        SET location_name = ?, location_country = ?, location_city = ?, location_meta = ?
        WHERE location_name = ? AND company_id = ?
    ''', (location_name, location_country, location_city, location_meta, location_name, g.company_id,))
    
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
    cur.execute('SELECT * FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id,))
    location = cur.fetchone()
    if not location:
        conn.close()
        abort(404, 'Location not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Location WHERE location_name = ? AND company_id = ?', (location_name, g.company_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200

# TABLA SENSOR

# Admin Crea un sensor
@app.route('/api/v1/sensor', methods=['POST'])
@require_admin
def created_sensor():
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtiene variables
    location_id = request.json('location_id')
    sensor_name = request.json('sensor_name')
    sensor_category = request.json('sensor_category')
    sensor_meta = request.json('sensor_meta')
    sensor_api_key = generate_api_key()

    cur.execute('INSERT INTO Sensor(location_id, sensor_name, sensor_category, sensor_meta, sensor_api_key) VALUES(?, ?, ?, ?, ?)', 
                (location_id, sensor_name, sensor_category, sensor_meta, sensor_api_key))
    conn.commit
    sensor_id = cur.lastrowid
    conn.close

    return jsonify({'sensor_id': sensor_id, 'sensor_api_key': sensor_api_key, 'message': 'Successfully created'}), 201


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
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', 
                (sensor_id, g.company_id,))
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
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?)', 
                (sensor_id, g.company_id,))
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
                (location_id, sensor_name, sensor_category, sensor_meta, sensor_id, g.company_id,))
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
    cur.execute('SELECT * FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?', 
                (sensor_id, g.company_id,))
    sensor = cur.fetchone()
    if not sensor:
        conn.close()
        abort(404, 'Sensor not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Sensor WHERE sensor_id = ? AND location_id IN (SELECT ID FROM Location WHERE company_id = ?', 
                (sensor_id, g.company_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200

# TABLA SENSOR_DATA

# Crea Sensor_Data
@app.route('/api/v1/sensor_data', methods=['POST'])
@require_sensor_api_key
def insert_sensor_data():
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtiene variables
    sensor_id = request.json('lsensor_id')
    data = request.json('data')

    cur.execute('INSERT INTO Sensor_Data(sensor_id, data) VALUES(?, ?)', 
                (sensor_id, data))
    conn.commit
    sensor_data_id = cur.lastrowid
    conn.close

    return jsonify({'sensor_data_id': sensor_data_id, 'message': 'Successfully created'}), 201

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

    # Crear la query para que acepte un arreglo de ids
    query = 'SELECT * FROM Sensor_Data WHERE sensor_id IN ({seq}) AND tiempo BETWEEN ? AND ?'
    query = query.format(seq=','.join(['?'] * len(sensor_ids)))
    conn = get_db_connection()
    cur = conn.cursor()

    # Crea la consulta con la query anterior, se entregan los ids y los tiempos
    cur.execute(query, sensor_ids + [from_time, to_time])
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Muestra uno de tabla Sensor_Data que se encuentre en el sensor de las ubicaciones de la compañía validada por api key
@app.route('/api/v1/sensor_data/<int:ID>', methods=['GET'])
@require_company_api_key
def get_sensor_data(ID):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Sensor_Data WHERE ID = ? AND sensor_id IN (SELECT sensor_id FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?))', 
                (ID, g.company_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        abort(404, 'Sensor not found')
    return jsonify(dict(row)), 200


# Edita en tabla Sensor_Data
@app.route('/api/v1/sensor_data/<int:ID>', methods=['PUT'])
@require_company_api_key
def update_sensor_data(ID):
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener el sensor data para ver si existe
    cur.execute('SELECT * FROM Sensor_Data WHERE ID = ? AND sensor_id IN (SELECT sensor_id FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?))', 
                (ID, g.company_id,))
    sensor_data = cur.fetchone()
    if not sensor_data:
        conn.close()
        abort(404, 'Sensor Data not found')

    # Actualizar sensor_data
    sensor_id = request.json('sensor_id')
    data = request.json('data')
    time = request.json('time')
    
    cur.execute('UPDATE Sensor_Data SET sensor_id = ?, data = ?, time = ? WHERE ID = ? AND sensor_id IN (SELECT sensor_id FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?))', 
                (sensor_id, data, time, ID, g.company_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated successfully'}), 200

# Elimina en tabla Sensor_Data
@app.route('/api/v1/sensor_data/<int:ID>', methods=['DELETE'])
@require_company_api_key
def delete_sensor_data(ID):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verificar si el sensor_data existe
    cur.execute('SELECT * FROM Sensor_Data WHERE ID = ? AND sensor_id IN (SELECT sensor_id FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?))', 
                (ID, g.company_id))
    sensor_data = cur.fetchone()
    if not sensor_data:
        conn.close()
        abort(404, 'Sensor data not found')
    
    # Eliminar la ubicación
    cur.execute('DELETE FROM Sensor_Data WHERE ID = ? AND sensor_id IN (SELECT sensor_id FROM Sensor WHERE location_id IN (SELECT ID FROM Location WHERE company_id = ?))', 
                (ID, g.company_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted successfully'}), 200


if __name__ == '__main__':
    init_db()
    print("Database and tables created successfully.")
    app.run(debug=True, host='0.0.0.0', port=8080)

# Para identificar errores
if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('errors')
