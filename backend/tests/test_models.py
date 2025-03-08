import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from models import Base, UserModel, AccessTokenModel
from settings import SECRET_KEY, ALGORITHM
from auth import get_password_hash

# テスト用のインメモリSQLiteデータベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# テスト用データベースの前処理と後処理
@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# テスト用ユーザーデータ
@pytest.fixture
def test_user_data():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "Password123"
    }

# テスト: ユーザーモデル作成
def test_create_user_model(test_db, test_user_data):
    # パスワードハッシュ化
    hashed_password = get_password_hash(test_user_data["password"])
    
    # ユーザーモデル作成
    user = UserModel(
        name=test_user_data["name"],
        email=test_user_data["email"],
        password_hash=hashed_password
    )
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # 検証
    assert user.id is not None
    assert user.name == test_user_data["name"]
    assert user.email == test_user_data["email"]
    assert user.password_hash != test_user_data["password"]  # パスワードがハッシュ化されていることを確認
    assert user.is_active == True
    
    # 名前の長さ制限（最大50文字）
    long_name_user = UserModel(
        name="A" * 51,  # 51文字の名前（制限を超える）
        email="longname@example.com",
        password_hash=hashed_password
    )
    test_db.add(long_name_user)
    # 長すぎる名前はデータベースレベルでは制限されないが、APIレベルでは検証される
    test_db.commit()

# テスト: アクセストークンモデル作成
def test_create_access_token_model(test_db, test_user_data):
    # ユーザー作成
    hashed_password = get_password_hash(test_user_data["password"])
    user = UserModel(
        name=test_user_data["name"],
        email=test_user_data["email"],
        password_hash=hashed_password
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # トークン作成
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    token = "test_jwt_token"
    
    access_token = AccessTokenModel(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
        is_active=True
    )
    
    test_db.add(access_token)
    test_db.commit()
    test_db.refresh(access_token)
    
    # 検証
    assert access_token.id is not None
    assert access_token.user_id == user.id
    assert access_token.token == token
    assert access_token.is_active == True
    assert access_token.expires_at > datetime.utcnow()
    
    # Usersとの関連を確認
    assert test_db.query(UserModel).filter(UserModel.id == access_token.user_id).first() is not None 
