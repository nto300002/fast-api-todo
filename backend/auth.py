from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models import UserModel, AccessTokenModel
from schemas import TokenData
from settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password) #平文のパスワードとハッシュ化されたパスワードを比較

def get_password_hash(password):
    return pwd_context.hash(password) #パスワードをハッシュ化

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(UserModel).filter(UserModel.email == email).first() #メールアドレスでユーザーを取得
    if not user:
        return False
    if not verify_password(password, user.password_hash): #パスワードが一致しない場合
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    #有効期限を設定↓
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    #JWTを作成↓
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)#署名 SECRET_KEYとALGORITHMを使用
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # まずJWTのデコードを試みる
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])#改ざんされていないか確認
        email: str = payload.get("sub")#サブクレーム?からメールアドレスを取得　ペイロード?
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError: #JWTのデコードに失敗した場合
        raise credentials_exception
    
    # トークンが無効化されていないか確認
    access_token = db.query(AccessTokenModel).filter(
        AccessTokenModel.token == token,
        AccessTokenModel.is_active == True,
        AccessTokenModel.expires_at > datetime.utcnow()
    ).first()
    
    if not access_token:
        raise credentials_exception
    
    # ユーザー情報を取得
    user = db.query(UserModel).filter(UserModel.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="無効なユーザー")
    return current_user
