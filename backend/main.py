from fastapi import FastAPI, Depends, APIRouter, HTTPException, status
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

from schemas import PostTodo, UserCreate, UserResponse, Token
from models import TodoModel, UserModel, AccessTokenModel
from settings import SessionLocal

from sqlalchemy.orm import Session

from typing import List

from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from auth import (
    authenticate_user, create_access_token, get_current_user, get_current_active_user,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

from database import get_db

app = FastAPI()
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # フロントエンドのオリジン
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)



# ユーザー管理クラス
class UserManager:
    def __init__(self):
        pass
        
    def get_users(self, db: Session):#ユーザー一覧を取得
        return db.query(UserModel).all()
    
    def create_user(self, user: UserCreate, db: Session):
        # バリデーションロジック
        if db.query(UserModel).filter(UserModel.email == user.email).first(): #メールアドレスが既に使用されている場合
            raise HTTPException(status_code=400, detail="メールアドレスが既に使用されています")
        
        # パスワードのハッシュ化
        hashed_password = get_password_hash(user.password)
        
        # ユーザー作成ロジック
        db_user = UserModel(
            name=user.name, 
            email=user.email,
            password_hash=hashed_password,
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

user_manager = UserManager()

# クラスメソッドをエンドポイントとして使用
@router.get("/users/", response_model=List[UserResponse]) #レスポンスの形式をUserResponseオブジェクトのリストとして指定（Pydanticモデルで自動的にバリデーションとシリアライズが行われる）
def get_users(db: Session = Depends(get_db)):
    return user_manager.get_users(db)  #処理を委譲

@router.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)): #リクエストとボディを　UserCreate型として受け取り、データベースセッションを依存性注入
    return user_manager.create_user(user, db)

app.include_router(router)


@app.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    expires_at = datetime.utcnow() + access_token_expires
    db_token = AccessTokenModel(
        user_id=user.id,
        token=access_token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/users/me", response_model=UserResponse)
def read_users_me(
    current_user: UserModel = Depends(get_current_active_user)
):
    return current_user

@app.post("/token/refresh", response_model=Token)
def refresh_token(current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email},
        expires_delta=access_token_expires
    )
    
    expires_at = datetime.utcnow() + access_token_expires
    db_token = AccessTokenModel(
        user_id=current_user.id,
        token=access_token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout")
def logout(
    current_user: UserModel = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # トークンを無効化
    db_token = db.query(AccessTokenModel).filter(
        AccessTokenModel.user_id == current_user.id,
        AccessTokenModel.token == token,
        AccessTokenModel.is_active == True
    ).first()
    
    if db_token:
        db_token.is_active = False
        db.commit()
    
    return {"message": "ログアウトしました"}

# 認証関連のエンドポイント
@app.get("/")
async def root():
    return {"message": "Hello World"}


# データベースからToDo一覧を取得するAPI
@app.get("/todo")
def get_todo(
        db: Session = Depends(get_db)
    ):
    # query関数でmodels.pyで定義したモデルを指定し、.all()関数ですべてのレコードを取得
    return db.query(TodoModel).all()

# ToDoを作成するAPI
@app.post("/todo")
def post_todo(
        todo: PostTodo, 
        db: Session = Depends(get_db)
    ):
    # 受け取ったtitleからモデルを作成
    db_model = TodoModel(title = todo.title)
    # データベースに登録（インサート）
    db.add(db_model)
    # 変更内容を確定
    db.commit()

    return {"message": "success"}

# ToDoを削除するAPI
@app.delete("/todo/{id}")
def delete_todo(
        id: int,
        db: Session = Depends(get_db)
    ):
    delete_todo = db.query(TodoModel).filter(TodoModel.id==id).one()
    db.delete(delete_todo)
    db.commit()

    return {"message": "success"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
