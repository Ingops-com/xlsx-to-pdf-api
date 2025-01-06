FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    libreoffice \
    python3 \
    python3-pip \
    && apt-get clean

# Crear directorio de la aplicación
WORKDIR /app

# Copiar archivos
COPY . /app

# Instalar dependencias de Python
RUN pip3 install -r requirements.txt

# Exponer el puerto de Flask
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python3", "main.py"]
