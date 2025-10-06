# app/routers/frontend.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, timedelta
from app.db import get_supabase

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def ui_dashboard(request: Request):
    # Datos de cabecera rápidos (contadores)
    sb = get_supabase()
    total_clientes = sb.table("clientes").select("id", count="exact").execute().count or 0
    total_matafuegos = sb.table("matafuegos").select("id", count="exact").execute().count or 0

    # Próximos 30 días para cabecera
    hoy = date.today()
    hasta = hoy + timedelta(days=30)
    proximos = sb.table("matafuegos") \
                 .select("id", count="exact") \
                 .gte("vencimiento", hoy.isoformat()) \
                 .lte("vencimiento", hasta.isoformat()) \
                 .execute().count or 0

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_clientes": total_clientes,
            "total_matafuegos": total_matafuegos,
            "proximos": proximos
        }
    )

@router.get("/partials/upcoming", response_class=HTMLResponse)
def ui_upcoming_partial(request: Request, dias:int=30):
    """Tabla de matafuegos que vencen entre hoy y hoy+días (opt-in True)."""
    sb = get_supabase()
    hoy = date.today()
    hasta = hoy + timedelta(days=dias)

    # Usamos la vista con join para traer nombre/telefono
    res = sb.table("vw_matafuegos_clientes") \
            .select("id_matafuego,nro_serie,tipo,vencimiento,nombre,telefono,empresa") \
            .eq("opt_in", True) \
            .gte("vencimiento", hoy.isoformat()) \
            .lte("vencimiento", hasta.isoformat()) \
            .order("vencimiento") \
            .execute()

    rows = res.data or []
    return templates.TemplateResponse(
        "partials/upcoming.html",
        {"request": request, "rows": rows, "hoy": hoy.isoformat(), "hasta": hasta.isoformat()}
    )
