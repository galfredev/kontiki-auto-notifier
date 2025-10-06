# app/routers/imports.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO, StringIO
from app.db import get_supabase

router = APIRouter()

REQUIRED = ["nombre", "telefono", "nro_serie", "tipo", "vencimiento"]
ALL_COLS = REQUIRED + ["ultima_recarga", "empresa", "opt_in"]

def _load_sheet(upload: UploadFile) -> pd.DataFrame:
    content = upload.file.read()
    if upload.filename.lower().endswith(".xlsx"):
        df = pd.read_excel(BytesIO(content), sheet_name=None)
        # usa "clientes" si existe, sino la primera hoja
        if isinstance(df, dict):
            df = df.get("clientes", list(df.values())[0])
    elif upload.filename.lower().endswith(".csv"):
        df = pd.read_csv(StringIO(content.decode("utf-8")))
    else:
        raise HTTPException(400, "Formato no soportado. Use .xlsx o .csv")
    df.columns = [c.strip().lower() for c in df.columns]
    return df

@router.post("/excel", response_class=HTMLResponse)
async def import_excel(file: UploadFile = File(...)):
    try:
        df = _load_sheet(file)
    except Exception as e:
        raise HTTPException(400, f"Error leyendo archivo: {e}")

    # Validación de columnas
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Faltan columnas obligatorias: {', '.join(missing)}")

    df = df[[c for c in ALL_COLS if c in df.columns]].copy()

    # Limpieza y defaults
    df["opt_in"] = df.get("opt_in", True).fillna(True).astype(bool)
    df["empresa"] = df.get("empresa", "").fillna("")
    df["ultima_recarga"] = df.get("ultima_recarga", "").fillna("")

    # Drop filas completamente vacías en obligatorios
    df = df.dropna(subset=["nombre","telefono","nro_serie","tipo","vencimiento"], how="any")

    # Inserción en Supabase
    sb = get_supabase()
    rows = df.to_dict(orient="records")
    inserted = 0
    errors = 0
    for row in rows:
        try:
            # upsert por nro_serie (ajustá la lógica a tus tablas reales)
            sb.table("clientes").upsert({
                "nombre": row["nombre"],
                "telefono": row["telefono"],
                "empresa": row.get("empresa",""),
                "opt_in": row.get("opt_in", True),
            }, on_conflict="telefono").execute()

            # matafuegos
            mf = {
                "nro_serie": row["nro_serie"],
                "tipo": row["tipo"],
                "vencimiento": str(row["vencimiento"])[:10],
                "ultima_recarga": str(row.get("ultima_recarga") or "")[:10] or None,
                "telefono": row["telefono"],  # FK simple por ahora
            }
            sb.table("matafuegos").upsert(mf, on_conflict="nro_serie").execute()
            inserted += 1
        except Exception:
            errors += 1

    html = f"""
    <div class="text-sm">
      <div><b>Importación completada</b></div>
      <div>Registros procesados: {inserted + errors}</div>
      <div><span style="color:#22c55e">✔</span> Insertados/actualizados: {inserted}</div>
      <div><span style="color:#ef4444">✖</span> Errores: {errors}</div>
    </div>
    """
    return HTMLResponse(html)
