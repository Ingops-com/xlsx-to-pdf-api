# -*- coding: utf-8 -*-

from flask import Flask, request, send_file, jsonify
from flasgger import Swagger
import os
import subprocess
import io

app = Flask(__name__)

# Configuración de Swagger
swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Excel to PDF API",
        "description": "API para convertir archivos de Excel a PDF",
        "version": "1.0.0"
    },
    "host": "178.16.141.125:5050",
    "basePath": "/",
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # Todas las rutas
            "model_filter": lambda tag: True,  # Todos los modelos
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "headers": [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    ]
}

swagger = Swagger(app, config=swagger_config)

UPLOAD_FOLDER = './static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/convert', methods=['POST'])
def convert_file():
    """
    Convierte un archivo de Excel a PDF.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: El archivo de Excel a convertir
    responses:
      200:
        description: El archivo PDF convertido
        content:
          application/pdf:
            schema:
              type: string
              format: binary
      400:
        description: Solicitud incorrecta
      500:
        description: Error interno del servidor
    """
    if 'file' not in request.files:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    # Guardar el archivo Excel en el directorio de subida
    input_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, file.filename))
    file.save(input_path)

    # Determinar el nombre esperado del archivo PDF generado
    pdf_name = os.path.splitext(file.filename)[0] + '.pdf'
    output_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, pdf_name))

    # Comando para convertir el archivo usando LibreOffice
    comando = f"libreoffice --headless --convert-to pdf --outdir {UPLOAD_FOLDER} {input_path}"
    proceso = subprocess.run(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Verificar si la conversión falló
    if proceso.returncode != 0:
        error_message = proceso.stderr.decode()
        # Borrar archivos en caso de error
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({"error": "Error al convertir el archivo", "details": error_message}), 500

    # Verificar si el archivo PDF fue generado
    if not os.path.exists(output_path):
        # Borrar archivo Excel si el PDF no se generó
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({"error": "El archivo PDF no fue encontrado"}), 500

    # Abrir el archivo PDF en binario
    with open(output_path, 'rb') as f:
        pdf_data = f.read()

    # Borrar los archivos después de leer su contenido
    if os.path.exists(input_path):
        os.remove(input_path)
    if os.path.exists(output_path):
        os.remove(output_path)

    # Retornar el archivo PDF desde la memoria
    return send_file(
        io.BytesIO(pdf_data),
        as_attachment=True,
        mimetype='application/pdf',
        download_name=pdf_name
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
