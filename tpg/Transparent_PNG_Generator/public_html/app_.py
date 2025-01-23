#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import time
import re
import html
import magic
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from .image_generator import generate_transparent_text

# 設定 (環境変数から取得、デフォルト値も設定)
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
FONTS_FOLDER = os.environ.get('FONTS_FOLDER', 'fonts')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
ALLOWED_EXTENSIONS = {'ttf', 'otf', 'ttc'}

# ディレクトリ作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FONTS_FOLDER, exist_ok=True)

# ログ設定
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file_path
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='../templates')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FONTS_FOLDER'] = FONTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

csrf = CSRFProtect(app)
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', 'default_csrf_secret')

# ファイル検証関数
def allowed_file(filename):
    if '.' not in filename:
        return False
    parts = filename.rsplit('.', 1)
    if len(parts) != 2: #分割結果が2つでない場合は不正なファイル名
        return False
    return parts[1].lower() in ALLOWED_EXTENSIONS

def verify_file_type(file_data):
    try:
        mime = magic.from_buffer(file_data, mime=True)
        return mime in ['font/ttf', 'font/otf', 'application/x-font-truetype', 'application/vnd.ms-opentype']
    except Exception as e:
        logger.exception("File type verification error: {}".format(e))
        return False

def save_file_safely(file_data, filename):
    try:
        filepath = os.path.join(app.config['FONTS_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(file_data)
        return True
    except Exception as e:
        logger.error(f"File save error: {str(e)}")  # ここを修正！
        return False

# サニタイズ関数
def sanitize_text(text):
    text = html.escape(text)
    return text

def validate_font_size(font_size, is_main_font):
    try:
        font_size = int(font_size)
        if is_main_font:
            if not 1 <= font_size <= 500:
                raise ValueError("Font size must be between 1 and 500.")
        else:
            if not 0 <= font_size <= 100:
                raise ValueError("Font size must be between 0 and 100.")
        return font_size
    except ValueError:
        raise ValueError("Invalid font size provided.")

def validate_color(color_code):
    if not re.match(r'^#[0-9a-fA-F]{6}$', color_code):
        raise ValueError("Invalid color code provided.")
    return color_code

def validate_line_height(line_height):
    try:
        line_height = float(line_height)
        if not 0.5 <= line_height <= 5.0:
            raise ValueError("Line height must be between 0.5 and 5.0.")
        return line_height
    except ValueError:
        raise ValueError("Invalid line height provided.")

def validate_font_name(font_name):
    if not re.match(r'^[\w\.\-]+$', font_name, re.IGNORECASE): # 正規表現を修正
        raise ValueError("Invalid font name provided.")
    return font_name

@app.before_request
def before_request():
    logger.debug(f'Before request: {request.method} {request.path}')

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        if request.method == 'POST':
            logger.info("Handling POST request to /")
            try:
                text = sanitize_text(request.form.get('text', ''))
                font_size = validate_font_size(request.form.get('fontSize', '16'), is_main_font=True)
                color = validate_color(request.form.get('color', '#000000'))
                font_name = validate_font_name(request.form.get('font', 'Arial'))
                line_height = validate_line_height(request.form.get('lineHeight', '1.5'))
                shadow_enabled = request.form.get('shadowEnabled') == 'on'
                shadow_blur = validate_font_size(request.form.get('shadowBlur', '5'), is_main_font=False)
                shadow_color = validate_color(request.form.get('shadowColor', '#000000'))
                outline_enabled = request.form.get('outlineEnabled') == 'on'
                outline_size = validate_font_size(request.form.get('outlineSize', '1'), is_main_font=False)
                outline_color = validate_color(request.form.get('outlineColor', '#000000'))
                gradient_enabled = request.form.get('gradientEnabled') == 'on'
                gradient_color = validate_color(request.form.get('gradientColor', '#000000'))

                if font_name.endswith(('.ttf', '.otf', '.ttc')):
                    font_path = os.path.join(app.config['FONTS_FOLDER'], font_name)
                    if not os.path.exists(font_path):
                        return jsonify({'error': "Uploaded font not found."}), 400
                    font_name = font_path

                timestamp = str(int(time.time() * 1000))
                filename = f'text_{timestamp}.png'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

                generate_transparent_text(
                    text=text,
                    output_path=filepath,
                    font_size=font_size,
                    color=color,
                    font_name=font_name,
                    line_height=line_height,
                    shadow_enabled=shadow_enabled,
                    shadow_blur=shadow_blur,
                    shadow_color=shadow_color,
                    outline_enabled=outline_enabled,
                    outline_size=outline_size,
                    outline_color=outline_color,
                    gradient_enabled=gradient_enabled,
                    gradient_color=gradient_color
                )

                logger.info(f"Image generated successfully: {filename}")
                return send_file(filepath, mimetype='image/png', as_attachment=True, download_name=filename)

            except ValueError as e:
                logger.warning(f"Input validation error: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.exception(f"Error during image generation: {e}")
                return jsonify({'error': gettext('upload_error')}), 500

        elif request.method == 'GET':
            logger.info("Handling GET request to /")
            return render_template('index.html')

    except Exception as e:
        logger.exception(f"An unexpected error occurred in index route: {e}")
        return "An unexpected error occurred. Please check the logs.", 500

@app.route('/fonts/<path:filename>')
def serve_font(filename):
    try:
        logger.info(f"Serving font file: {filename}")
        if not allowed_file(filename):
            logger.warning(f"Invalid font file requested: {filename}")
            return jsonify({'error': gettext('invalid_file_type')}), 400
        fonts_dir = os.path.join(app.root_path, '..', 'fonts')
        return send_from_directory(fonts_dir, filename)
    except Exception as e:
        logger.exception(f"An error occurred while serving font: {e}")
        return "An error occurred. Please check the logs.", 500

@app.route('/upload-font', methods=['POST'])
def upload_font():
    try:
        logger.info("Handling font upload")
        if 'font' not in request.files:
            logger.warning("No file part in request")
            return jsonify({'error': gettext('no_font_selected')}), 400

        font_file = request.files['font']
        if font_file.filename == '':
            logger.warning("No selected file")
            return jsonify({'error': gettext('no_font_selected')}), 400

        file_data = font_file.read()
        file_size = len(file_data)
        logger.info(f"Uploaded font file size: {file_size} bytes")

        if file_size > MAX_CONTENT_LENGTH:
            logger.warning(f"File size too large: {file_size} bytes")
            return jsonify({'error': gettext('file_size_error')}), 400
        
        if not verify_file_type(file_data):
            return jsonify({'error': gettext('invalid_file_type')}), 400

        filename = secure_filename(font_file.filename)
        if not save_file_safely(file_data, filename):
            return jsonify({'error': gettext('upload_error')}), 500

        logger.info(f"Font file uploaded successfully: {filename}")
        return jsonify({
            'message': gettext('upload_success'),
            'fontName': filename
        })
    except Exception as e:
        logger.exception(f"Font upload error: {e}")
        return jsonify({'error': gettext('upload_error')}), 500

# ... (generate, terms, privacy, contact, switch_language, error handlers, その他の関数は変更なし)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=50)