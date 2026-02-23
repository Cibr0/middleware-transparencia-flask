from pydantic import BaseModel, Field
from typing import Optional

class Produto(BaseModel):
    id: int
    title: str
    description: str
    price: float = Field(ge=0)
    category: Optional[str] = None