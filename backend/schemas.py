from pydantic import BaseModel,EmailStr, Field, field_validator, model_validator
from typing import Optional

class PostTodo(BaseModel):
    title: str
    description: Optional[str] = None
    
    model_config = {
        "from_attributes": True  # orm_modeの代わり
    }

class UserBase(BaseModel):
    name: str = Field(..., max_length=50)
    email: EmailStr
    

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    # パスワードのバリデーション
    @field_validator('password')
    @classmethod
    def password_validation(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError('パスワードには少なくとも1つの大文字が必要です')
        if not any(char.islower() for char in v):
            raise ValueError('パスワードには少なくとも1つの小文字が必要です')
        if not any(char.isdigit() for char in v):
            raise ValueError('パスワードには少なくとも1つの数字が必要です')
        return v

class UserResponse(UserBase):
    id: int
    
    model_config = {
        "from_attributes": True  # orm_modeの代わり
    }

# 複数フィールドの相互検証の例（オプション）
class TimeRangeExample(BaseModel):
    start_time: str
    end_time: str
    
    # 複数フィールドにまたがるバリデーション
    @model_validator(mode='after')
    def check_times(self):
        if self.start_time >= self.end_time:
            raise ValueError('終了時間は開始時間より後である必要があります')
        return self

# 追加のスキーマ
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
