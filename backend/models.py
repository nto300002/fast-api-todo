from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from settings import Base


class TodoModel(Base):
    __tablename__ = 'todo'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    created_date = Column(DateTime, default=datetime.utcnow)

class UserModel(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    profile_picture_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class AccessTokenModel(Base):
    __tablename__ = 'access_token'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    token = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    