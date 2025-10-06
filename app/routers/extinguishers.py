from fastapi import APIRouter, HTTPException
from app.db import get_supabase
from app.models import ExtinguisherIn, Extinguisher

router = APIRouter()

@router.post("/", response_model=Extinguisher)
def create_extinguisher(payload: ExtinguisherIn):
    sb = get_supabase()
    resp = sb.table("matafuegos").insert(payload.model_dump()).execute()
    if not resp.data:
        raise HTTPException(400, "No se pudo crear el matafuego")
    return resp.data[0]

@router.get("/", response_model=list[Extinguisher])
def list_extinguishers():
    sb = get_supabase()
    return sb.table("matafuegos").select("*").order("id").execute().data
