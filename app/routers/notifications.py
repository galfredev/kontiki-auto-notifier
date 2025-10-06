# app/routers/notifications.py
from fastapi import APIRouter
from datetime import date, timedelta, datetime
from app.db import get_supabase
from app.utils.whatsapp import (
    send_template_recordatorio,
    send_template_ultimo_aviso,
)

router = APIRouter()
DIAS_AVISO = [30, 15, 7, 1, 0]

def _fmt_ymd_to_dmy(ymd: str) -> str:
    """Convierte 'YYYY-MM-DD' -> 'DD/MM/YYYY'."""
    return datetime.strptime(ymd[:10], "%Y-%m-%d").strftime("%d/%m/%Y")

def run_today_job():
    sb = get_supabase()
    hoy = date.today()
    enviados: list[dict] = []

    for d in DIAS_AVISO:
        target = (hoy + timedelta(days=d)).isoformat()
        res = sb.rpc("vencen_en_fecha", {"fecha_objetivo": target}).execute()
        rows = res.data or []

        for item in rows:
            nombre = item["nombre"]
            tel = item["telefono"]
            serie = item["nro_serie"]
            venc = _fmt_ymd_to_dmy(item["vencimiento"])

            # Elegimos plantilla
            if d == 0:
                ok, error = send_template_ultimo_aviso(tel, nombre, serie, venc)
                plantilla = "ultimo_aviso_es"
            else:
                ok, error = send_template_recordatorio(tel, nombre, serie, venc)
                plantilla = "recordatorio_vencimiento_es"

            # Registrar envío
            sb.table("avisos").insert({
                "matafuego_id": item["id_matafuego"],
                "fecha_envio": hoy.isoformat(),
                "plantilla": f"{plantilla} (D-{d})",
                "estado": "sent" if ok else "error",
                "error": error
            }).execute()

            enviados.append({
                "tel": tel, "d": d, "ok": ok,
                "plantilla": plantilla, "error": error
            })

    return {"hoy": hoy.isoformat(), "enviados": enviados}

@router.post("/run-today")
def run_today():
    return run_today_job()
