# -*- coding: utf-8 -*-

from flask import Flask, request, send_file, jsonify
from flasgger import Swagger
from werkzeug.utils import secure_filename
import os
import subprocess
import io
import tempfile
import shutil
import logging

app = Flask(__name__)

# ----------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------

# Tamaño máximo de subida (ejemplo: 20 MB)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

# Extensiones permitidas (Excel + Word + formatos similares)
ALLOWED_EXTENSIONS = {
    # Excel
    '.xls', '.xlsx', '.xlsm', '.xlsb', '.ods',
    # Word
    '.doc', '.docx', '.odt'
}

# Timeout para la conversión con LibreOffice (en segundos)
CONVERSION_TIMEOUT = 120

# Configuración de logging básico
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Configuración de Swagger
# ----------------------------------------------------------------------
swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Office to PDF API",
        "description": "API para convertir archivos de Excel o Word a PDF usando LibreOffice",
        "version": "1.1.0"
    },
    # Ajusta el host si lo usas detrás de proxy o con dominio
    "host": "178.16.141.125:5050",
    "basePath": "/",
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
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

# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------

def allowed_file_extension(filename: str) -> bool:
    """
    Verifica si la extensión del archivo está permitida.
    (Excel, Word u otros formatos de LibreOffice incluidos en ALLOWED_EXTENSIONS)
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def build_libreoffice_command(input_path: str, outdir: str) -> list:
    """
    Construye el comando para ejecutar LibreOffice en modo headless.
    Se usa lista en lugar de shell=True para mayor seguridad.
    """
    return [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        outdir,
        input_path
    ]

# ----------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health_check():
    """
    Verifica que la API esté viva.
    ---
    responses:
      200:
        description: La API está funcionando
    """
    return jsonify({"status": "ok"}), 200


@app.route('/convert', methods=['POST'])
def convert_file():
    """
    Convierte un archivo de Excel o Word a PDF.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Archivo de Excel o Word a convertir en PDF
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
      413:
        description: Archivo demasiado grande
      500:
        description: Error interno del servidor
    """
    # Validar que venga el archivo
    if 'file' not in request.files:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    filename = secure_filename(file.filename)

    if not allowed_file_extension(filename):
        return jsonify({
            "error": "Extensión de archivo no permitida",
            "allowed_extensions": list(ALLOWED_EXTENSIONS)
        }), 400

    # Crear directorio temporal por solicitud (evita colisiones y mejora la concurrencia)
    temp_dir = tempfile.mkdtemp(prefix="office2pdf_")
    input_path = os.path.join(temp_dir, filename)

    try:
        # Guardar archivo de entrada
        file.save(input_path)
        logger.info(f"Archivo recibido y guardado en: {input_path}")

        # Nombre esperado para el PDF
        base_name, _ = os.path.splitext(filename)
        pdf_name = base_name + '.pdf'
        output_path = os.path.join(temp_dir, pdf_name)

        # Construir el comando
        command = build_libreoffice_command(input_path, temp_dir)

        # Ejecutar LibreOffice
        logger.info(f"Iniciando conversión con LibreOffice: {command}")
        proceso = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=CONVERSION_TIMEOUT
        )

        if proceso.returncode != 0:
            stderr = proceso.stderr.decode(errors="ignore")
            stdout = proceso.stdout.decode(errors="ignore")
            logger.error(f"Error en LibreOffice (returncode {proceso.returncode})")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return jsonify({
                "error": "Error al convertir el archivo",
                "details": stderr.strip() or stdout.strip()
            }), 500

        # Verificar que el PDF exista
        if not os.path.exists(output_path):
            logger.error(f"No se encontró el PDF generado en: {output_path}")
            return jsonify({"error": "El archivo PDF no fue generado"}), 500

        # Leer el PDF a memoria
        with open(output_path, 'rb') as f:
            pdf_data = f.read()

        logger.info(f"Conversión completada correctamente para: {filename}")

        # Retornar el archivo PDF desde memoria
        return send_file(
            io.BytesIO(pdf_data),
            as_attachment=True,
            mimetype='application/pdf',
            download_name=pdf_name
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout al convertir el archivo: {filename}")
        return jsonify({
            "error": "Timeout al convertir el archivo",
            "details": f"La conversión excedió los {CONVERSION_TIMEOUT} segundos permitidos."
        }), 500

    except Exception as e:
        logger.exception("Error inesperado durante la conversión")
        return jsonify({
            "error": "Error interno del servidor",
            "details": str(e)
        }), 500

    finally:
        # Eliminar el directorio temporal completo y todo su contenido
        try:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Directorio temporal eliminado: {temp_dir}")
        except Exception as e:
            # No romper la respuesta por un error limpiando archivos
            logger.warning(f"No se pudo eliminar el directorio temporal {temp_dir}: {e}")


# ----------------------------------------------------------------------
# Manejo de errores globales
# ----------------------------------------------------------------------

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "error": "El archivo es demasiado grande",
        "details": "Supera el tamaño máximo permitido por el servidor."
    }), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Ruta no encontrada"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    # Nota: muchos errores 500 ya se manejan dentro de convert_file con más detalle
    logger.error(f"Error 500 no controlado: {error}")
    return jsonify({
        "error": "Error interno del servidor"
    }), 500


# ----------------------------------------------------------------------
# Arranque de la aplicación
# ----------------------------------------------------------------------

if __name__ == '__main__':
    # En producción es recomendable usar un servidor WSGI (gunicorn, uWSGI, etc.)
    app.run(host='0.0.0.0', port=5050)
