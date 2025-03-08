import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import time

from main import app, get_db
from models import Base, UserModel, AccessTokenModel
from settings import SECRET_KEY, ALGORITHM
from datetime import datetime, timedelta
from auth import get_current_user, get_current_active_user

# テスト用のインメモリSQLiteデータベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPIのDI（依存性注入）をオーバーライド
@pytest.fixture
def client():
    # テスト用DBの依存性
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # DBの初期化
    Base.metadata.create_all(bind=engine)
    
    # 依存性のオーバーライド
    app.dependency_overrides[get_db] = override_get_db
    
    # テストクライアント作成
    with TestClient(app) as test_client:
        yield test_client
    
    # テスト後のクリーンアップ
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}

# テスト用ユーザーデータ
@pytest.fixture
def user_data():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "Password123"
    }

# テスト: ユーザー登録
def test_register_user(client, user_data):
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert "id" in data
    assert "password" not in data  # パスワードはレスポンスに含まれない

# テスト: パスワードバリデーション
def test_password_validation(client, user_data):
    # 大文字がない
    invalid_user = user_data.copy()
    invalid_user["password"] = "password123"
    response = client.post("/users/", json=invalid_user)
    assert response.status_code == 422  # バリデーションエラー
    
    # 小文字がない
    invalid_user["password"] = "PASSWORD123"
    response = client.post("/users/", json=invalid_user)
    assert response.status_code == 422
    
    # 数字がない
    invalid_user["password"] = "PasswordABC"
    response = client.post("/users/", json=invalid_user)
    assert response.status_code == 422

# テスト: ユーザーログイン
def test_login_user(client, user_data):
    # ユーザー登録
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200, f"ユーザー登録失敗: {response.text}"
    
    # ログイン
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"ログイン失敗: {response.text}"
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # 不正なログイン（間違ったパスワード）
    invalid_login = {
        "username": user_data["email"],
        "password": "WrongPassword123"
    }
    response = client.post("/token", data=invalid_login)
    assert response.status_code == 401

# テスト: 保護されたリソースへのアクセス
def test_protected_resource(client, user_data):
    # ユーザー登録
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200, f"ユーザー登録失敗: {response.text}"
    
    # ログイン
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"ログイン失敗: {response.text}"
    token = response.json()["access_token"]
    
    # 認証ヘッダー
    headers = {"Authorization": f"Bearer {token}"}
    
    # 保護されたリソースへのアクセス
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200, f"認証リソースアクセス失敗: {response.text}"
    user_info = response.json()
    assert user_info["email"] == user_data["email"]
    
    # 認証なしでアクセス
    response = client.get("/users/me")
    assert response.status_code == 401

# テスト: ログアウト
def test_logout(client, user_data):
    # ユーザー登録
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200, f"ユーザー登録失敗: {response.text}"
    
    # ログイン
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"ログイン失敗: {response.text}"
    token = response.json()["access_token"]
    
    # 認証ヘッダー
    headers = {"Authorization": f"Bearer {token}"}
    
    # まず認証付きリソースにアクセスできることを確認
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200, f"認証リソースアクセス失敗: {response.text}"
    
    # ログアウト
    response = client.post("/logout", headers=headers)
    assert response.status_code == 200, f"ログアウト失敗: {response.text}"
    
    # 少し待機（非同期処理のための時間）
    time.sleep(0.1)
    
    # ログアウト後、同じトークンでのアクセスを試みる
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401, f"ログアウト後のアクセスが拒否されていません: {response.text}"  # 認証失敗
