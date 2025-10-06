# Kon-Tiki | Notificaciones

Sistema de avisos automáticos por WhatsApp (Cloud API) para vencimientos de matafuegos.

## Requisitos
- Python 3.11+ / 3.12
- Supabase (URL + Service Key)
- WhatsApp Cloud API (Phone ID + Access Token)

## Setup local
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # completar claves
uvicorn app.main:app --reload
