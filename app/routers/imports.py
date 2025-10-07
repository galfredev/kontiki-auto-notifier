from fastapi import APIRouter, UploadFile, Request
from fastapi.responses import HTMLResponse
from app.db import get_supabase
from datetime import datetime
import pandas as pd
import re
import unicodedata

router = APIRouter()

# -------------------------------
# Normalización de headers
# -------------------------------

def _slug(s: str) -> str:
    """Minúsculas, sin acentos, sin paréntesis y con guiones bajos para comparar."""
    s = (s or "").strip().lower()
    # quitar texto entre paréntesis para permitir "telefono (+e.164)"
    s = re.sub(r"\(.*?\)", "", s)
    # quitar acentos
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    # reemplazar separadores por _
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s

# Mapeo flexible de columnas -> nombre canónico
ALIASES = {
    "nombre": {"nombre", "cliente", "razon_social", "contacto"},
    "telefono": {
        "telefono", "telefono_e_164", "telefono_e164", "telefono_e_16",
        "celular", "whatsapp", "telefono_movil", "tel", "telefono_movil_e164"
    },
    "nro_serie": {
        "nro_serie", "nroserie", "numero_de_serie", "num_serie", "serie", "nro_de_serie", "ns"
    },
    "tipo": {"tipo", "tipo_equipo", "clase"},
    "peso_kg": {"peso_kg", "peso", "kg", "peso_en_kg"},
    "vencimiento": {
        "vencimiento", "vence", "fecha_de_vencimiento", "fecha_vencimiento", "vto", "vencim"
    },
    "ultima_recarga": {
        "ultima_recarga", "fecha_ultima_recarga", "ult_recarga", "recarga", "ultima_rec"
    },
    "empresa": {"empresa", "compania", "company", "negocio"},
    "opt_in": {"opt_in", "acepta_avisos", "permite_avisos", "consentimiento", "acepta"},
}

# invertimos el diccionario para buscar rápido
ALIAS_LOOKUP = {}
for canon, variants in ALIASES.items():
    for v in variants:
        ALIAS_LOOKUP[_slug(v)] = canon


def _map_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapped = []
    for col in df.columns:
        key = _slug(col)
        mapped.append(ALIAS_LOOKUP.get(key, _slug(col)))  # si no mapea, deja el slug
    df.columns = mapped
    return df


# -------------------------------
# Utilidades varias
# -------------------------------

E164 = re.compile(r"^\+\d{8,15}$")

def normalize_phone_ar(raw) -> str | None:
    """Intenta normalizar teléfonos (Argentina). Devuelve E.164 o None si es irrecuperable."""
    if raw is None:
        return None
    s = str(raw).strip()

    # quitar todo lo que no sea dígito o +
    s = re.sub(r"[^\d+]", "", s)

    # 00.. -> +..
    if s.startswith("00"):
        s = "+" + s[2:]

    # agregar + si no lo tiene
    if not s.startswith("+"):
        s = "+" + s

    # dejar solo dígitos tras el +
    s = "+" + re.sub(r"\D", "", s[1:])

    # si no hay país, asumir AR (+549...)
    if not s.startswith("+54"):
        digits = re.sub(r"\D", "", s)
        if digits.startswith("0"):
            digits = digits[1:]
        s = "+549" + digits  # asumimos móvil

    # si es AR y no tiene el 9, insertarlo
    if s.startswith("+54") and not s.startswith("+549"):
        s = "+549" + s[3:]

    if not E164.match(s):
        return None

    return s


def _to_date(x):
    """Acepta YYYY-MM-DD, fechas Excel o vacío -> None"""
    if x is None or str(x).strip() == "":
        return None
    try:
        # pandas maneja bien muchos formatos
        d = pd.to_datetime(x)
        return d.strftime("%Y-%m-%d")
    except Exception:
        # último intento: forzar string
        try:
            return pd.to_datetime(str(x)).strftime("%Y-%m-%d")
        except Exception:
            return None


# -------------------------------
# Import principal
# -------------------------------

@router.post("/excel", response_class=HTMLResponse)
async def import_excel(request: Request, file: UploadFile):
    sb = get_supabase()

    # Leer Excel o CSV
    fname = (file.filename or "").lower()
    if fname.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file.file)
    else:
        df = pd.read_csv(file.file)

    # Mapear cabeceras flexibles -> canon
    df = _map_headers(df)

    # Requeridos mínimos para poder crear registros
    required = ["nombre", "telefono", "nro_serie", "tipo", "vencimiento"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return HTMLResponse(
            f"<p style='color:#f88'>Faltan columnas: {', '.join(missing)}</p>"
            "<p>Tips: acepto variaciones como 'telefono (+E.164)', 'vence', "
            "'nro serie', 'última recarga', etc.</p>"
        )

    processed = len(df)
    inserted = 0
    errores: list[str] = []

    for i, row in df.iterrows():
        try:
            nombre = str(row.get("nombre", "")).strip()
            telefono_raw = row.get("telefono", "")
            telefono = normalize_phone_ar(telefono_raw)
            if not telefono:
                raise ValueError(f"Teléfono inválido/irrecuperable: {telefono_raw}")

            nro_serie = str(row.get("nro_serie", "")).strip()
            tipo = str(row.get("tipo", "")).strip()
            empresa = str(row.get("empresa", "")).strip() if "empresa" in df.columns else None
            opt_in = bool(row.get("opt_in", True)) if "opt_in" in df.columns else True

            vencimiento = _to_date(row.get("vencimiento"))
            if not vencimiento:
                raise ValueError(f"Vencimiento inválido: {row.get('vencimiento')}")

            ultima = _to_date(row.get("ultima_recarga")) if "ultima_recarga" in df.columns else None

            # (Opcional) peso_kg: lo ignoramos si tu DB no tiene esa columna
            # peso = row.get("peso_kg") if "peso_kg" in df.columns else None

            # Upsert de cliente por teléfono
            c = sb.table("clients").upsert({
                "nombre": nombre,
                "telefono": telefono,
                "empresa": empresa,
                "opt_in": opt_in
            }, on_conflict="telefono").execute().data

            if c:
                client_id = c[0]["id"]
            else:
                client_id = sb.table("clients").select("id").eq("telefono", telefono).limit(1).execute().data[0]["id"]

            # Upsert de matafuego por nro_serie
            payload = {
                "client_id": client_id,
                "nro_serie": nro_serie,
                "tipo": tipo,
                "vencimiento": vencimiento,
                "ultima_recarga": ultima
            }
            sb.table("extinguishers").upsert(payload, on_conflict="nro_serie").execute()

            inserted += 1

        except Exception as e:
            errores.append(f"Fila {i+2}: {e}")  # +2 por header y base 1

    # Respuesta HTML
    html = [
        "<div style='margin-top:6px'>",
        "<b>Importación completada</b><br>",
        f"✔ Registros procesados: {processed}<br>",
        f"✔ Insertados/actualizados: {inserted}<br>",
        f"✖ Errores: {len(errores)}<br>",
    ]
    if errores:
        html.append("<ul style='margin-top:6px'>" + "".join([f"<li>{e}</li>" for e in errores]) + "</ul>")
    html.append("</div>")
    return HTMLResponse("".join(html))
