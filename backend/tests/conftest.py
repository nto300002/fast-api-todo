import os
import sys
import pytest

# 親ディレクトリをPYTHONPATHに追加（テストのインポート問題解決用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 共通のfixture等を定義する場合はここに追加 
