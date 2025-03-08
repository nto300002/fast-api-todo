from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import secrets

SQLALCHEMY_DATABASE_URL = 'sqlite:///sample.sqlite'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# JWT認証の設定
# 本番環境では環境変数から読み込むなど、より安全な方法で管理することをお勧めします
SECRET_KEY = secrets.token_hex(32)  # ランダムな秘密鍵を生成
ALGORITHM = "HS256"  # JWT署名アルゴリズム
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # アクセストークンの有効期限（分）
