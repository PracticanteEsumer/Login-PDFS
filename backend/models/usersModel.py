# models.py
from pydantic import BaseModel
from typing import List, Optional

class UserBase(BaseModel):
    str_name_user: str
    str_email: str
    # Se omite la contraseña en la respuesta por razones de seguridad
    # str_password: str

class User(UserBase):
    id_user_PK: int
    id_permissionFK: int
    id_areaFK: int

    class Config:
        orm_mode = True  # Permite a Pydantic trabajar con objetos ORM (como los de SQLAlchemy)

class UserCreate(UserBase):
    str_password: str  # Para la creación, se incluye la contraseña

class UserUpdate(BaseModel):
    str_name_user: Optional[str] = None
    str_email: Optional[str] = None
    str_password: Optional[str] = None
