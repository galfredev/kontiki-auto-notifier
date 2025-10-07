import os, requests

PHONE_ID = os.getenv("META_WABA_PHONE_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

def send_whatsapp(to: str, nombre: str, vencimiento: str) -> bool:
    if not (PHONE_ID and ACCESS_TOKEN):
        return False

    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "aviso_vencimiento",   # usa tu plantilla aprobada
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": nombre},
                    {"type": "text", "text": vencimiento}
                ]
            }]
        }
    }
    r = requests.post(url, headers=headers, json=data, timeout=20)
    print("Meta:", r.status_code, r.text)
    return 200 <= r.status_code < 300
