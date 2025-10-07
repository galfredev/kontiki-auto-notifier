from fastapi import FastAPI
from app.routers import clients, extinguishers, notifications, imports, testsend, frontend
from app.utils.scheduler import attach_scheduler

app = FastAPI(
    title="Kon-Tiki Notifier",
    description="API para notificar vencimientos de matafuegos por WhatsApp",
    version="0.1.0",
)
from fastapi.staticfiles import StaticFiles

# ... después de crear `app = FastAPI(...)`:
app.mount("/static", StaticFiles(directory="app/static"), name="static")
from app.routers import reports
app.include_router(reports.router, prefix="/reports", tags=["Reportes"])

app.include_router(frontend.router, tags=["UI"])  # "/"
app.include_router(clients.router,        prefix="/clients",        tags=["Clientes"])
app.include_router(extinguishers.router,  prefix="/extinguishers",  tags=["Matafuegos"])
app.include_router(notifications.router,  prefix="/notifications",  tags=["Notificaciones"])
app.include_router(imports.router,        prefix="/import",         tags=["Importación"])
app.include_router(testsend.router,       prefix="/testsend",       tags=["Tests"])

attach_scheduler(app)
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root_redirect():
    # opcional: podrías redirigir a la UI, pero ya la montamos en "/"
    return {"ok": True, "app": "Kon-Tiki Notifier 🚒"}
