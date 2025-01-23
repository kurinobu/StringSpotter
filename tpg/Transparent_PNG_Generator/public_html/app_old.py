import os
import logging
import time
import threading
import re
import html
import magic
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory, g, session, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .image_generator import generate_transparent_text # . を追加
from werkzeug.utils import secure_filename

# ファイルパスの更新
# 'logs' ディレクトリが存在しなければ作成
log_dir = os.path.join(os.path.dirname(__file__), 'logs') # __file__ で app.py のパスを取得
os.makedirs(log_dir, exist_ok=True)

# ログの設定 (修正)
log_file_path = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO, # 必要に応じてlogging.DEBUGなどに変更
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file_path
)
logger = logging.getLogger(__name__) # loggerオブジェクトを取得

app = Flask(__name__, static_folder='static', template_folder='../templates')
# セッションの設定強化
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# CSRFプロテクション
csrf = CSRFProtect(app)
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY')

# Flaskアプリケーションのインスタンス作成後に追加
@app.before_request
def before_request():
    logging.debug('Before request: %s', request.path)


# Secure Headers Configuration
@app.after_request
def add_security_headers(response):
    """セキュリティヘッダーの追加"""
    # HSTS: HTTPS使用を強制
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # X-Frame-Options: クリックジャッキング対策
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # X-Content-Type-Options: MIMEタイプスニッフィング対策
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # X-XSS-Protection: ブラウザのXSSフィルター有効化
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer-Policy: リファラー情報の制御
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions-Policy: ブラウザ機能の制限
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # Content Security Policy
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", 'https://cdn.jsdelivr.net'],
        'style-src': ["'self'", 'https://cdn.jsdelivr.net', "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'blob:'],
        'font-src': ["'self'", 'https://cdn.jsdelivr.net'],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'form-action': ["'self'"],
        'base-uri': ["'self'"],
        'object-src': ["'none'"]
    }

    # CSPディレクティブの構築
    csp_string = '; '.join(f"{key} {' '.join(values)}" for key, values in csp.items())
    response.headers['Content-Security-Policy'] = csp_string

    return response

# Language configuration
app.config['LANGUAGES'] = {
    'en': 'English',
    'ja': '日本語'
}

# Translation dictionary
TRANSLATIONS = {
    'en': {
        'text_image_generator': 'Transparent PNG Generator',
        'generate_text_image': 'Generate transparent PNG images with your text',
        'enter_text': 'Enter Text',
        'font_size': 'Font Size',
        'upload_font': 'Upload Font',
        'generate': 'Generate',
        'file_size_error': 'File size is too large (max 10MB)',
        'invalid_file_type': 'Invalid file type (allowed: .ttf, .otf, .ttc)',
        'no_font_selected': 'No font file selected',
        'upload_success': 'Font uploaded successfully',
        'upload_error': 'Error occurred during upload',
        'max_chars': '(Max 100 characters)',
        'chars_remaining': 'Characters remaining',
        'line_height': 'Line Height',
        'text_color': 'Text Color',
        'font': 'Font',
        'preview': 'Preview',
        'preview_text': 'Preview Text',
        'terms_of_service': 'Terms of Service',
        'privacy_policy': 'Privacy Policy',
        'contact': 'Contact',
        'supported_formats': 'Supported formats: TTF, OTF, TTC (max 10MB)',
        'custom_font_prefix': 'Custom',
        'font_upload_error': 'Font upload failed',
        'text_required': 'Text input is required',
        'text_too_long': 'Text exceeds maximum length of 100 characters',
        'invalid_font_size': 'Invalid font size (must be between 8 and 72)',
        'invalid_color': 'Invalid color code format',
        'invalid_font': 'Invalid font selection',
        'invalid_line_height': 'Invalid line height (must be between 1.0 and 2.5)',
        'terms_title': 'Terms of Service',
        'terms_service_usage_title': 'Service Usage',
        'terms_service_usage_content': 'By using this service, you agree to comply with these terms and all applicable laws and regulations.',
        'terms_prohibited_title': 'Prohibited Actions',
        'terms_prohibited_content': 'The following actions are prohibited when using this service:',
        'terms_prohibited_1': 'Using the service for illegal purposes or in violation of any laws',
        'terms_prohibited_2': 'Uploading malicious content or attempting to compromise the service',
        'terms_prohibited_3': 'Interfering with other users\' access to the service',
        'terms_disclaimer_title': 'Disclaimer',
        'terms_disclaimer_content': 'This service is provided "as is" without any warranties. We are not responsible for any damages arising from the use of this service.',
        'privacy_title': 'Privacy Policy',
        'privacy_collection_title': 'Information Collection',
        'privacy_collection_content': 'We collect minimal information necessary to provide our service, including temporary storage of uploaded fonts and generated images.',
        'privacy_usage_title': 'Information Usage',
        'privacy_usage_content': 'The collected information is used solely for providing the service and is automatically deleted after a short period.',
        'privacy_protection_title': 'Information Protection',
        'privacy_protection_content': 'We implement security measures to protect your information from unauthorized access or disclosure.',
        'privacy_contact_title': 'Contact Information',
        'privacy_contact_content': 'If you have any questions about our privacy policy, please contact us.',
        'contact_title': 'Contact Us',
        'contact_content': 'If you have any questions or concerns, please feel free to contact us at:'
    },
    'ja': {
        'text_image_generator': '透過PNGジェネレーター',
        'generate_text_image': '透過PNGテキスト画像を生成',
        'enter_text': 'テキストを入力',
        'font_size': 'フォントサイズ',
        'upload_font': 'フォントをアップロード',
        'generate': '生成',
        'file_size_error': 'ファイルサイズが大きすぎます（最大10MB）',
        'invalid_file_type': '無効なファイル形式です（許可：.ttf、.otf、.ttc）',
        'no_font_selected': 'フォントファイルが選択されていません',
        'upload_success': 'フォントを正常にアップロードしました',
        'upload_error': 'アップロード中にエラーが発生しました',
        'max_chars': '（最大100文字）',
        'chars_remaining': '残り文字数',
        'line_height': '行間',
        'text_color': 'テキストカラー',
        'font': 'フォント',
        'preview': 'プレビュー',
        'preview_text': 'プレビューテキスト',
        'terms_of_service': 'ご利用規約',
        'privacy_policy': 'プライバシーポリシー',
        'contact': 'お問い合わせ',
        'supported_formats': 'TTF、OTF、TTCフォーマット対応（最大10MB）',
        'custom_font_prefix': 'カスタム',
        'font_upload_error': 'フォントのアップロードに失敗しました',
        'text_required': 'テキストを入力してください',
        'text_too_long': 'テキストが最大文字数（100文字）を超えています',
        'invalid_font_size': '無効なフォントサイズです（8から72の間で指定してください）',
        'invalid_color': '無効なカラーコード形式です',
        'invalid_font': '無効なフォント選択です',
        'invalid_line_height': '無効な行の高さです（1.0から2.5の間で指定してください）',
        'terms_title': 'ご利用規約',
        'terms_service_usage_title': 'サービスのご利用について',
        'terms_service_usage_content': '本サービスをご利用いただくことで、お客様はこれらの利用規約および適用される法令に従うことに同意したものとみなされます。',
        'terms_prohibited_title': '禁止事項',
        'terms_prohibited_content': '本サービスのご利用にあたり、以下の行為を禁止します：',
        'terms_prohibited_1': '違法行為または法令に違反する目的での利用',
        'terms_prohibited_2': '悪意のあるコンテンツのアップロードやサービスを危険にさらす行為',
        'terms_prohibited_3': '他のユーザーのサービス利用を妨げる行為',
        'terms_disclaimer_title': '免責事項',
        'terms_disclaimer_content': '本サービスは「現状有姿」で提供され、いかなる保証もいたしかねます。本サービスの利用に起因するいかなる損害についても、当社は責任を負いかねます。',
        'privacy_title': 'プライバシーポリシー',
        'privacy_collection_title': '情報収集について',
        'privacy_collection_content': '当社は、アップロードされたフォントや生成された画像の一時的な保存を含む、サービス提供に必要最小限の情報のみを収集いたします。',
        'privacy_usage_title': '情報の利用について',
        'privacy_usage_content': '収集した情報は、サービス提供の目的にのみ使用され、短期間後に自動的に削除されます。',
        'privacy_protection_title': '情報保護について',
        'privacy_protection_content': '当社は、お客様の情報を不正アクセスや漏洩から保護するためのセキュリティ対策を実施しています。',
        'privacy_contact_title': 'お問い合わせ',
        'privacy_contact_content': 'プライバシーポリシーに関するご質問がございましたら、お問い合わせください。',
        'contact_title': 'お問い合わせ',
        'contact_content': 'ご質問やご不明な点がございましたら、お気軽にお問い合わせください：'
    }
}

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window-elastic-expiry"  # より安全な戦略を使用
)

def get_locale():
    """現在の言語を取得"""
    if 'lang' not in session:
        # ブラウザの設定から言語を取得
        browser_lang = request.accept_languages.best_match(app.config['LANGUAGES'].keys())
        session['lang'] = browser_lang or 'en'
    return session['lang']

def gettext(key):
    """翻訳を取得"""
    lang = get_locale()
    translations = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    return translations.get(key, key)

@app.context_processor
def utility_processor():
    """テンプレートで使用する関数を追加"""
    return {
        'gettext': gettext,
        'get_locale': get_locale,
        'languages': app.config['LANGUAGES']
    }

# アップロードディレクトリの設定を更新
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = 'tpg/Transparent_PNG_Generator/upload'
app.config['FONTS_FOLDER'] = 'tpg/Transparent_PNG_Generator/fonts'
app.config['CLEANUP_INTERVAL'] = 1800  # 30分
app.config['FILE_EXPIRY'] = 1800  # 30分

# 必要なディレクトリの作成
for directory in [app.config['UPLOAD_FOLDER'], app.config['FONTS_FOLDER']]:
    os.makedirs(directory, exist_ok=True)
    # パーミッションの設定
    os.chmod(directory, 0o755)


# Allowed file types and their magic numbers
ALLOWED_EXTENSIONS = {'ttf', 'otf', 'ttc'}
ALLOWED_MIME_TYPES = {
    'ttf': ['font/ttf', 'application/x-font-ttf'],
    'otf': ['font/otf', 'application/x-font-opentype'],
    'ttc': ['font/collection', 'application/x-font-ttf']
}

def allowed_file(filename):
    """ファイル拡張子の検証"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def verify_file_type(file_data):
    """ファイルの内容を検証"""
    try:
        # libmagicを使用してファイルタイプを検出
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file_data)

        # ファイルの拡張子を取得
        filename = secure_filename(request.files['font'].filename)
        ext = filename.rsplit('.', 1)[1].lower()

        # MIMEタイプの検証（より広範なタイプを許可）
        allowed_mime_types = [
            'font/ttf', 'application/x-font-ttf',
            'font/otf', 'application/x-font-opentype',
            'font/collection', 'application/x-font-ttf',
            'application/octet-stream',  # バイナリファイルとして検出される場合も許可
            'font/sfnt',  # macOSで使用される一般的なフォントMIMEタイプ
            'application/font-sfnt'  # 別のSFNTベースのフォントMIMEタイプ
        ]

        if file_type not in allowed_mime_types:
            logging.warning(f"Invalid MIME type: {file_type} for extension: {ext}")
            return False

        # フォントファイルの追加検証
        # TTF/OTFファイルの基本的な構造をチェック
        if ext in ['ttf', 'otf']:
            # フォントファイルの一般的なマジックナンバーをチェック
            magic_numbers = [
                b'\x00\x01\x00\x00',  # TTFの標準的なマジックナンバー
                b'OTTO',              # OTFの標準的なマジックナンバー
                b'true',              # TrueTypeフォントの別のマジックナンバー
                b'typ1'               # Type1フォントのマジックナンバー
            ]

            # いずれかのマジックナンバーで始まるかチェック
            if not any(file_data.startswith(magic) for magic in magic_numbers):
                logging.warning("Invalid font file structure")
                return False

        return True
    except Exception as e:
        logging.error(f"File verification error: {str(e)}")
        return False

def get_file_hash(file_data):
    """ファイルのハッシュ値を計算"""
    return hashlib.sha256(file_data).hexdigest()

def save_file_safely(file_data, filename):
    """ファイルを安全に保存"""
    try:
        filepath = os.path.join(app.config['FONTS_FOLDER'], filename)

        # 既存のファイルを削除（同名ファイルの上書き）
        if os.path.exists(filepath):
            os.remove(filepath)

        # ファイルを書き込む
        with open(filepath, 'wb') as f:
            f.write(file_data)

        # パーミッションを制限
        os.chmod(filepath, 0o644)

        return True
    except Exception as e:
        logging.error(f"File save error: {str(e)}")
        return False

def cleanup_old_files():
    """古い一時ファイルを定期的に削除"""
    while True:
        try:
            current_time = time.time()
            # フォントファイルの削除
            for filename in os.listdir(app.config['FONTS_FOLDER']):
                filepath = os.path.join(app.config['FONTS_FOLDER'], filename)
                if os.path.getctime(filepath) + app.config['FILE_EXPIRY'] < current_time:
                    try:
                        os.remove(filepath)
                        logging.info(f"古いフォントファイルを削除しました: {filename}")
                    except OSError as e:
                        logging.error(f"フォントファイルの削除に失敗しました {filename}: {e}")

            # 生成された画像の削除
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.startswith('text_') and filename.endswith('.png'):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.getctime(filepath) + app.config['FILE_EXPIRY'] < current_time:
                        try:
                            os.remove(filepath)
                            logging.info(f"古い画像ファイルを削除しました: {filename}")
                        except OSError as e:
                            logging.error(f"画像ファイルの削除に失敗しました {filename}: {e}")

        except Exception as e:
            logging.error(f"クリーンアップ処理中にエラーが発生しました: {e}")

        time.sleep(app.config['CLEANUP_INTERVAL'])

# クリーンアップスレッドの開始
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fonts/<path:filename>')
def serve_font(filename):
    """フォントファイルを提供するルート"""
    if not allowed_file(filename):
        return jsonify({'error': gettext('invalid_file_type')}), 400
    return send_from_directory(app.config['FONTS_FOLDER'], filename)

@app.route('/upload-font', methods=['POST'])
@limiter.limit("10 per minute")  # 1分間に10回まで
def upload_font():
    """フォントファイルのアップロード処理"""
    try:
        if 'font' not in request.files:
            return jsonify({'error': gettext('no_font_selected')}), 400

        font_file = request.files['font']
        if font_file.filename == '':
            return jsonify({'error': gettext('no_font_selected')}), 400

        if not allowed_file(font_file.filename):
            return jsonify({'error': gettext('invalid_file_type')}), 400

        # ファイルを一時的にメモリに読み込んでチェック
        file_data = font_file.read()
        file_size = len(file_data)
        logging.info(f"Uploaded font file size: {file_size} bytes")

        # ファイルサイズの検証
        if file_size > MAX_CONTENT_LENGTH:
            logging.warning(f"File size too large: {file_size} bytes")
            return jsonify({'error': gettext('file_size_error')}), 400

        # ファイルタイプの検証
        if not verify_file_type(file_data):
            return jsonify({'error': gettext('invalid_file_type')}), 400

        # ファイル名の安全化
        filename = secure_filename(font_file.filename)

        # ファイルの保存
        if not save_file_safely(file_data, filename):
            return jsonify({'error': gettext('upload_error')}), 500

        logging.info(f"Font file uploaded successfully: {filename}")

        return jsonify({
            'message': gettext('upload_success'),
            'fontName': filename
        })

    except Exception as e:
        logging.error(f"Font upload error: {str(e)}")
        return jsonify({'error': gettext('upload_error')}), 500

# 入力値の検証とサニタイズ処理を行う関数を追加
def sanitize_text(text, error_messages=None):
    """テキスト入力のサニタイズ処理"""
    if error_messages is None:
        error_messages = {
            'text_required': gettext('text_required'),
            'text_too_long': gettext('text_too_long')
        }

    if not text or not isinstance(text, str):
        raise ValueError(error_messages['text_required'])
    # HTMLエスケープ処理
    sanitized = html.escape(text.strip())
    if len(sanitized) > 100:  # 最大文字数の制限
        raise ValueError(error_messages['text_too_long'])
    # 制御文字の削除（改行とタブは許可）
    sanitized = ''.join(char for char in sanitized if char >= ' ' or char in '\n\t')
    return sanitized

def validate_font_size(size, error_messages=None, is_main_font=True):
    """フォントサイズの検証"""
    if error_messages is None:
        error_messages = {
            'invalid_font_size': gettext('invalid_font_size')
        }

    try:
        if isinstance(size, str):
            size = size.strip()
        size = int(float(size))  # float経由で変換することで、小数点の文字列も処理可能

        # メインのフォントサイズとエフェクトのサイズで異なる範囲をチェック
        if is_main_font:
            if not (8 <= size <= 72):  # メインフォントサイズの範囲チェック
                logging.warning(f"Invalid main font size (not in range 8-72): {size}")
                raise ValueError
        else:
            if not (1 <= size <= 20):  # エフェクト用サイズの範囲チェック
                logging.warning(f"Invalid effect size (not in range 1-20): {size}")
                raise ValueError
        return size
    except (ValueError, TypeError) as e:
        logging.error(f"Font size validation error: {str(e)} for input: {size}")
        raise ValueError(error_messages['invalid_font_size'])

def validate_color(color, error_messages=None):
    """カラーコードの検証"""
    if error_messages is None:
        error_messages = {
            'invalid_color': gettext('invalid_color')
        }

    if not isinstance(color, str):
        raise ValueError(error_messages['invalid_color'])
    # カラーコードの形式チェック（#RRGGBBまたは#RRGGBBAA）
    if not re.match(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$', color):
        raise ValueError(error_messages['invalid_color'])
    return color

def validate_font_name(font_name, error_messages=None):
    """フォント名の検証"""
    if error_messages is None:
        error_messages = {
            'invalid_font': gettext('invalid_font')
        }

    if not isinstance(font_name, str):
        logging.error(f"Invalid font name type: {type(font_name)}")
        raise ValueError(error_messages['invalid_font'])

    # 基本フォントの場合
    allowed_fonts = {'Arial', 'Helvetica', 'Times New Roman', 'Courier New'}
    if font_name in allowed_fonts:
        return font_name

    # カスタムフォントの場合
    if font_name.endswith(('.ttf', '.otf', '.ttc')):
        secured_filename = secure_filename(font_name)
        font_path = os.path.join(app.config['FONTS_FOLDER'], secured_filename)
        if os.path.exists(font_path):
            return secured_filename
        logging.error(f"Font file not found: {font_path}")

    logging.error(f"Invalid font name: {font_name}")
    raise ValueError(error_messages['invalid_font'])

def validate_line_height(line_height, error_messages=None):
    """行の高さの検証"""
    if error_messages is None:
        error_messages = {
            'invalid_line_height': gettext('invalid_line_height')
        }

    try:
        height = float(line_height)
        if not (1.0 <= height <= 2.5):  # 行の高さの範囲チェック
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(error_messages['invalid_line_height'])
    return height


@app.route('/generate', methods=['POST'])
@limiter.limit("30 per minute")  # 1分間に30回まで
def generate():
    """画像生成処理"""
    try:
        logging.info(f"Received form data: {request.form}")
        # 入力値の取得とサニタイズ
        text = sanitize_text(request.form.get('text', ''))
        font_size = validate_font_size(request.form.get('fontSize', '16'), is_main_font=True)
        logging.info(f"Validated font size: {font_size}")
        color = validate_color(request.form.get('color', '#000000'))
        font_name = validate_font_name(request.form.get('font', 'Arial'))
        line_height = validate_line_height(request.form.get('lineHeight', '1.5'))

        # スタイル効果パラメータの取得と検証（エフェクトサイズ用の別の範囲で検証）
        shadow_enabled = request.form.get('shadowEnabled') == 'on'
        shadow_blur = validate_font_size(request.form.get('shadowBlur', '5'), is_main_font=False)
        shadow_color = validate_color(request.form.get('shadowColor', '#000000'))

        outline_enabled = request.form.get('outlineEnabled') == 'on'
        outline_size = validate_font_size(request.form.get('outlineSize', '1'), is_main_font=False)
        outline_color = validate_color(request.form.get('outlineColor', '#000000'))

        gradient_enabled = request.form.get('gradientEnabled') == 'on'
        gradient_color = validate_color(request.form.get('gradientColor', '#000000'))

        logging.debug(f"入力パラメータ: text={text}, font_size={font_size}, color={color}, "
                     f"font_name={font_name}, line_height={line_height}, "
                     f"shadow_enabled={shadow_enabled}, shadow_blur={shadow_blur}, "
                     f"outline_enabled={outline_enabled}, outline_size={outline_size}, "
                     f"gradient_enabled={gradient_enabled}")

        # カスタムフォントの処理
        if font_name.endswith(('.ttf', '.otf', '.ttc')):
            font_path = os.path.join(app.config['FONTS_FOLDER'], font_name)
            if not os.path.exists(font_path):
                return jsonify({'error': gettext('upload_error')}), 400
            font_name = font_path

        # タイムスタンプ付きのファイル名を生成
        timestamp = str(int(time.time() * 1000))
        filename = f'text_{timestamp}.png'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

        # 画像生成
        from public_html.image_generator import generate_transparent_text
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

        logging.info(f"画像を生成しました: {filename}")
        return send_file(filepath, mimetype='image/png', as_attachment=True, download_name=filename)

    except ValueError as e:
        logging.warning(f"入力値エラー: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"画像生成中にエラーが発生しました: {str(e)}")
        return jsonify({'error': gettext('upload_error')}), 500

# 新しいルートを追加
@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/switch_language/<lang>')
def switch_language(lang):
    """言語切り替えのエンドポイント"""
    if lang in app.config['LANGUAGES']:
        session['lang'] = lang
        return redirect(request.referrer or url_for('index'))
    return 'Invalid language', 400

@app.errorhandler(400)
def handle_csrf_error(e):
    """CSRFエラーのハンドリング"""
    return jsonify({'error': gettext('csrf_error')}), 400

@app.errorhandler(429)
def ratelimit_handler(e):
    """レート制限エラーのハンドリング"""
    return jsonify({
        'error': gettext('rate_limit_error'),
        'retry_after': e.description
    }), 429


if __name__ == '__main__':
    # 本番環境では直接実行しない
    app.run(host='0.0.0.0', port=5000)