from fastapi import APIRouter, HTTPException
from app.db import get_supabase
from app.models import ClientIn, Client

router = APIRouter()

@router.post("/", response_model=Client)
def create_client(payload: ClientIn):
    sb = get_supabase()
    resp = sb.table("clientes").insert(payload.model_dump()).execute()
    if not resp.data:
        raise HTTPException(400, "No se pudo crear el cliente")
    return resp.data[0]

@router.get("/", response_model=list[Client])
def list_clients():
    sb = get_supabase()
    return sb.table("clientes").select("*").order("id").execute().data
