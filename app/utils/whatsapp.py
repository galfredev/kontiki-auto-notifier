# app/utils/whatsapp.py
import os, requests
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient  # queda por compatibilidad

load_dotenv()
PROVIDER = os.getenv("WHATSAPP_PROVIDER", "meta")

# ---- META CLOUD API ----
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PHONE_ID = os.getenv("META_WABA_PHONE_ID")

def _meta_post(payload: dict) -> tuple[bool, str | None]:
    if not META_TOKEN or not META_PHONE_ID:
        return False, "Faltan META_ACCESS_TOKEN o META_WABA_PHONE_ID"
    url = f"https://graph.facebook.com/v20.0/{META_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    return (True, None) if r.ok else (False, r.text)

def send_whatsapp_template(to_e164: str, template_name: str, lang_code: str, params: list[str]) -> tuple[bool, str | None]:
    """Envía una plantilla con parámetros al body."""
    components = [{
        "type": "body",
        "parameters": [{"type": "text", "text": p} for p in params]
    }]
    payload = {
        "messaging_product": "whatsapp",
        "to": to_e164,
        "type": "template",
        "template": {"name": template_name, "language": {"code": lang_code}, "components": components}
    }
    return _meta_post(payload)

# Plantillas de Kon-Tiki
def send_template_recordatorio(to_e164: str, nombre: str, serie: str, fecha_venc: str):
    # plantilla: recordatorio_vencimiento_es (es_AR) -> vars: 1 nombre, 2 nro_serie, 3 fecha
    return send_whatsapp_template(to_e164, "recordatorio_vencimiento_es", "es_AR", [nombre, serie, fecha_venc])

def send_template_ultimo_aviso(to_e164: str, nombre: str, serie: str, fecha_venc: str):
    # plantilla: ultimo_aviso_es (es_AR) -> vars: 1 nombre, 2 nro_serie, 3 fecha
    return send_whatsapp_template(to_e164, "ultimo_aviso_es", "es_AR", [nombre, serie, fecha_venc])

# ---- TWILIO opcional (si alguna vez querés usarlo) ----
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM")

def _send_twilio(to_e164: str, body: str):
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        return False, "Config Twilio faltante"
    try:
        TwilioClient(TWILIO_SID, TWILIO_TOKEN).messages.create(
            from_=TWILIO_FROM, to=f"whatsapp:{to_e164}", body=body
        )
        return True, None
    except Exception as e:
        return False, str(e)
