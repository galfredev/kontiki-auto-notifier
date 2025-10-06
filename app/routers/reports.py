# app/routers/reports.py
from fastapi import APIRouter, Response, Query
from datetime import date, timedelta, datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from io import BytesIO
from app.db import get_supabase

router = APIRouter()

def _fetch_rows(dias: int):
    sb = get_supabase()
    hoy = date.today()
    hasta = hoy + timedelta(days=dias)
    res = (sb.table("vw_matafuegos_clientes")
             .select("nombre,telefono,nro_serie,tipo,vencimiento")
             .eq("opt_in", True)
             .gte("vencimiento", hoy.isoformat())
             .lte("vencimiento", hasta.isoformat())
             .order("vencimiento")
             .execute())
    return res.data or []

@router.get("/vencimientos", summary="Descargar PDF de vencimientos")
def pdf_vencimientos(dias: int = Query(30, ge=1, le=365)):
    rows = _fetch_rows(dias)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Encabezado
    c.setFillColor(HexColor("#ef4444"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, h-2*cm, "Kon-Tiki | Notificaciones")
    c.setFillColor(HexColor("#333333"))
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, h-2.6*cm, f"Reporte de vencimientos (próx. {dias} días) — generado {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Columnas
    y = h - 3.4*cm
    c.setFillColor(HexColor("#111111"))
    c.rect(2*cm, y-0.4*cm, w-4*cm, 0.6*cm, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 10)
    cols = ["Vence", "Cliente", "Teléfono", "Serie", "Tipo"]
    x_cols = [2.1*cm, 5*cm, 10.4*cm, 14.5*cm, 17.2*cm]
    for i, t in enumerate(cols):
        c.drawString(x_cols[i], y-0.15*cm, t)
    y -= 1*cm

    # Filas
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#222222"))
    for i, r in enumerate(rows):
        if y < 2.5*cm:
            c.showPage(); y = h - 2*cm
            c.setFont("Helvetica", 10); c.setFillColor(HexColor("#222222"))
        venc = datetime.strptime(r["vencimiento"][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        vals = [venc, r["nombre"], r["telefono"], r["nro_serie"], r["tipo"] or "-"]
        # líneas sutiles
        c.setFillColor(HexColor("#f5f5f5") if (i%2)==0 else HexColor("#ededed"))
        c.rect(2*cm, y-0.3*cm, w-4*cm, 0.5*cm, fill=1, stroke=0)
        c.setFillColor(HexColor("#111111"))
        for j, val in enumerate(vals):
            c.drawString(x_cols[j], y-0.12*cm, str(val)[:32])
        y -= 0.7*cm

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()

    headers = {"Content-Disposition": f'attachment; filename="vencimientos_{dias}d.pdf"'}
    return Response(pdf, media_type="application/pdf", headers=headers)
