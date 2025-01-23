import sys
import os

# venv のパスを指定 (実際のパスに合わせて修正)
activate_this = os.path.join(
    '/home/users/2/main.jp-50364279a98534b5/web/tpg/Transparent_PNG_Generator/public_html/.venv/bin/activate_this.py'
)
if os.path.exists(activate_this): # ファイルが存在する場合のみ実行
    exec(open(activate_this).read(), dict(__file__=activate_this))

# Flask アプリケーションのパスを指定 (app.py のあるディレクトリ)
sys.path.insert(0, '/home/users/2/main.jp-50364279a98534b5/web/tpg/Transparent_PNG_Generator/public_html/')

from app import app as application # app.py から app インスタンスをインポート

# ログ出力 (デバッグ用)
import logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logging.error("app.wsgi loaded")