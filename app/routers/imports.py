from fastapi import APIRouter, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from app.db import get_supabase
from datetime import datetime
import pandas as pd
import re

router = APIRouter()
E164 = re.compile(r"^\+\d{8,15}$")

def _to_date(x):
    if not x or str(x).strip() == "":
        return None
    # acepta 'YYYY-MM-DD' o Excel serial
    if isinstance(x, (int, float)):
        # pandas ya convierte, pero por si llega serial crudo
        return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(x), unit="D")
    return pd.to_datetime(str(x))

@router.post("/excel", response_class=HTMLResponse)
async def import_excel(request: Request, file: UploadFile):
    sb = get_supabase()
    df = pd.read_excel(file.file) if file.filename.endswith(("xlsx","xls")) else pd.read_csv(file.file)

    # normalizar columnas
    df.columns = [c.strip().lower() for c in df.columns]
    required = ["nombre","telefono","nro_serie","tipo","vencimiento"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return HTMLResponse(f"<p style='color:#f88'>Faltan columnas: {', '.join(missing)}</p>")

    processed = len(df)
    inserted = 0
    errores = []

    for i, row in df.iterrows():
        try:
            nombre = str(row.get("nombre","")).strip()
            telefono = str(row.get("telefono","")).strip()
            nro_serie = str(row.get("nro_serie","")).strip()
            tipo = str(row.get("tipo","")).strip()
            empresa = str(row.get("empresa","")).strip() if "empresa" in df.columns else None
            opt_in = bool(row.get("opt_in", True)) if "opt_in" in df.columns else True

            if not E164.match(telefono):
                raise ValueError(f"Teléfono no es E.164 (+549...): {telefono}")

            venc = _to_date(row.get("vencimiento"))
            if venc is None:
                raise ValueError("Vencimiento vacío")
            venc = pd.to_datetime(venc).strftime("%Y-%m-%d")

            ultima = _to_date(row.get("ultima_recarga")) if "ultima_recarga" in df.columns else None
            ultima = pd.to_datetime(ultima).strftime("%Y-%m-%d") if ultima else None

            # upsert client por teléfono
            c = sb.table("clients").upsert({
                "nombre": nombre,
                "telefono": telefono,
                "empresa": empresa,
                "opt_in": opt_in
            }, on_conflict="telefono").execute().data

            client_id = c[0]["id"] if c else sb.table("clients").select("id").eq("telefono",telefono).limit(1).execute().data[0]["id"]

            # upsert extinguisher por nro_serie
            sb.table("extinguishers").upsert({
                "client_id": client_id,
                "nro_serie": nro_serie,
                "tipo": tipo,
                "vencimiento": venc,
                "ultima_recarga": ultima
            }, on_conflict="nro_serie").execute()

            inserted += 1

        except Exception as e:
            errores.append(f"Fila {i+2}: {e}")  # +2 por header + base 1

    html = [
        "<div style='margin-top:6px'>",
        f"<b>Importación completada</b><br>",
        f"✔ Registros procesados: {processed}<br>",
        f"✔ Insertados/actualizados: {inserted}<br>",
        f"✖ Errores: {len(errores)}<br>",
    ]
    if errores:
        html.append("<ul>" + "".join([f"<li>{e}</li>" for e in errores]) + "</ul>")
    html.append("</div>")
    return HTMLResponse("".join(html))
