from pydantic import BaseModel
from typing import Optional

class PostTodo(BaseModel):
    title: str
    description: Optional[str] = None
    
    class Config:
        orm_mode = True 
