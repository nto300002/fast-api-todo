import pytest
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException

from auth import (
    get_password_hash, verify_password, 
    create_access_token, authenticate_user,
    get_current_user
)
from models import UserModel, AccessTokenModel
from settings import SECRET_KEY, ALGORITHM
from tests.test_models import test_db, test_user_data  # 共通のfixture再利用

# パスワードハッシュ化のテスト
def test_password_hashing():
    password = "Password123"
    hashed_password = get_password_hash(password)
    
    # ハッシュ化されたパスワードは元のパスワードと異なる
    assert hashed_password != password
    
    # ハッシュ化されたパスワードは検証に成功する
    assert verify_password(password, hashed_password) == True
    
    # 間違ったパスワードは検証に失敗する
    assert verify_password("WrongPassword", hashed_password) == False

# JWTトークン生成と検証のテスト
def test_jwt_token_creation():
    # トークンデータ
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=30)
    
    # トークン生成
    token = create_access_token(data, expires_delta)
    
    # トークンが文字列で返される
    assert isinstance(token, str)
    
    # トークンが正しくデコードできる
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"
    
    # 有効期限が設定されている
    assert "exp" in payload
    
    # 期限切れトークンの作成
    expired_token_data = {"sub": "test@example.com"}
    expired_delta = timedelta(minutes=-30)  # 過去の時間
    expired_token = create_access_token(expired_token_data, expired_delta)
    
    # 期限切れトークンはデコード時にエラーが発生する
    with pytest.raises(jwt.JWTError):
        jwt.decode(
            expired_token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"verify_exp": True}
        )

# ユーザー認証テスト
def test_authenticate_user(test_db, test_user_data):
    # ユーザー作成
    hashed_password = get_password_hash(test_user_data["password"])
    user = UserModel(
        name=test_user_data["name"],
        email=test_user_data["email"],
        password_hash=hashed_password
    )
    test_db.add(user)
    test_db.commit()
    
    # 正しい認証情報で認証
    authenticated_user = authenticate_user(
        test_db, 
        test_user_data["email"], 
        test_user_data["password"]
    )
    assert authenticated_user is not False
    assert authenticated_user.email == test_user_data["email"]
    
    # 存在しないユーザーで認証
    non_existent_user = authenticate_user(
        test_db, 
        "nonexistent@example.com", 
        test_user_data["password"]
    )
    assert non_existent_user is False
    
    # 間違ったパスワードで認証
    wrong_password_user = authenticate_user(
        test_db, 
        test_user_data["email"], 
        "WrongPassword123"
    )
    assert wrong_password_user is False

# アクセストークン検証テスト
def test_access_token_validation(test_db, test_user_data):
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
    token_data = {"sub": user.email}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(token_data, expires_delta)
    
    # アクセストークンをDBに保存
    expires_at = datetime.utcnow() + expires_delta
    db_token = AccessTokenModel(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    test_db.add(db_token)
    test_db.commit()
    
    # トークンを無効化した場合
    db_token.is_active = False
    test_db.commit()
    
    # 無効化されたトークンでユーザー取得を試みるとエラーになる
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(token=token, db=test_db)
    assert excinfo.value.status_code == 401
    
    # トークンを再度有効化
    db_token.is_active = True
    test_db.commit()
    
    # 有効なトークンでユーザー取得
    current_user = get_current_user(token=token, db=test_db)
    assert current_user.id == user.id
    assert current_user.email == user.email 
