from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class ClientIn(BaseModel):
    nombre: str
    telefono: str = Field(description="Formato E.164, ej +5493511234567")
    empresa: Optional[str] = None
    opt_in: bool = True

class Client(ClientIn):
    id: int

class ExtinguisherIn(BaseModel):
    cliente_id: int
    nro_serie: str
    tipo: str
    vencimiento: date
    ultima_recarga: Optional[date] = None

class Extinguisher(ExtinguisherIn):
    id: int

class NoticeIn(BaseModel):
    matafuego_id: int
    plantilla: str

class Notice(BaseModel):
    id: int
    matafuego_id: int
    fecha_envio: date
    plantilla: str
    estado: str
    error: Optional[str] = None
