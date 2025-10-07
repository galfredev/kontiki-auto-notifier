from fastapi import APIRouter, Header, HTTPException
import os
from datetime import date
from app.db import get_supabase
from app.utils.whatsapp import send_whatsapp

router = APIRouter()

CRON_SECRET = os.getenv("CRON_SECRET", "")

def _find_due_today(sb):
    today = date.today().isoformat()
    # extinguisher + client join (dos queries)
    exts = sb.table("extinguishers").select("*").eq("vencimiento", today).execute().data
    out = []
    for e in exts:
        c = sb.table("clients").select("*").eq("id", e["client_id"]).limit(1).execute().data
        if c:
            out.append({"ext": e, "client": c[0]})
    return out

@router.post("/run-today")
def run_today():
    sb = get_supabase()
    items = _find_due_today(sb)
    sent = 0; errors = 0
    for it in items:
        nombre = it["client"]["nombre"]
        telefono = it["client"]["telefono"]
        venc = it["ext"]["vencimiento"]
        ok = send_whatsapp(telefono, nombre, venc)
        if ok:
            sent += 1
            sb.table("avisos").insert({
                "extinguisher_id": it["ext"]["id"],
                "estado": "sent",
                "detalle": {"to": telefono}
            }).execute()
        else:
            errors += 1
            sb.table("avisos").insert({
                "extinguisher_id": it["ext"]["id"],
                "estado": "error",
                "detalle": {"to": telefono}
            }).execute()
    return {"sent": sent, "errors": errors}

@router.post("/run-daily")
def run_daily(x_cron_key: str = Header(None)):
    if x_cron_key != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return run_today()
