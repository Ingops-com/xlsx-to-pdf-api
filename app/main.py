from flask import Flask, request, send_file, jsonify
from flasgger import Swagger
import os
import subprocess

app = Flask(__name__)

# Configuración de Swagger
swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Excel to PDF API",
        "description": "API to convert Excel files to PDF",
        "version": "1.0.0"
    },
    "host": "localhost:5000",
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
    Convert an Excel file to PDF.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The Excel file to convert
    responses:
      200:
        description: The converted PDF file
        content:
          application/pdf:
            schema:
              type: string
              format: binary
      400:
        description: Bad Request
      500:
        description: Internal Server Error
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

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
        return jsonify({"error": "Failed to convert file", "details": error_message}), 500

    # Verificar si el archivo PDF fue generado
    if not os.path.exists(output_path):
        return jsonify({"error": "Output file not found"}), 500

    # Retornar el archivo PDF
    return send_file(output_path, as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
