# app/routers/testsend.py
from fastapi import APIRouter, Query
from app.utils.whatsapp import send_template_recordatorio

router = APIRouter()

@router.post("/recordatorio")
def test_recordatorio(
    to: str = Query(..., description="Destino E.164, ej +549351..."),
    nombre: str = Query("Cliente"),
    serie: str = Query("KT-0001"),
    venc: str = Query("2025-12-01")
):
    ok, err = send_template_recordatorio(to, nombre, serie, venc)
    return {"ok": ok, "error": err}
