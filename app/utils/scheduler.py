# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from app.routers.notifications import run_today_job

def attach_scheduler(app: FastAPI):
    sched = BackgroundScheduler(timezone="America/Argentina/Buenos_Aires")
    sched.add_job(run_today_job, trigger="cron", hour=9, minute=0, id="daily_notifications")
    sched.start()
    print("[SCHED] Programado job diario 09:00")

    @app.on_event("shutdown")
    def shutdown_event():
        sched.shutdown()
        print("[SCHED] Apagado")
