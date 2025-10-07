from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Kon-Tiki | Notificaciones")

# Static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Routers
from app.routers import imports, notifications, reports, frontend
app.include_router(frontend.router, tags=["UI"])  # dashboard + partials
app.include_router(imports.router, prefix="/import", tags=["Importaciones"])
app.include_router(notifications.router, prefix="/notifications", tags=["Avisos"])
app.include_router(reports.router, prefix="/reports", tags=["Reportes"])

# Health check (Render)
@app.get("/health")
def health():
    return {"ok": True}
