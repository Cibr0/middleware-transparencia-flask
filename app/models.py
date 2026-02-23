from pydantic import BaseModel, Field
from datetime import datetime

class Meta(BaseModel):
    createdAt: datetime
    updatedAt: datetime

class Produto(BaseModel):
    id: int
    title: str
    price: float = Field(ge=0)
    meta: Meta