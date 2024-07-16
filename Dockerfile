# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos necesarios al contenedor
COPY requirements.txt requirements.txt
COPY . .

# Instala las dependencias
RUN pip install -r requirements.txt

# Expone el puerto en el que correrá la aplicación
EXPOSE 8080

# Comando para correr la aplicación
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
