import sys
sys.path.insert(0, '/home/users/2/main.jp-50364279a98534b5/web/tpg/Transparent_PNG_Generator')

from public_html import app # public_htmlディレクトリからapp.pyをインポート

application = app.app # Flaskアプリケーションのインスタンスを取得

# 環境変数はここで設定しない！
