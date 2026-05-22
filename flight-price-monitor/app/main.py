from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Alert, FlightPrice, MonitorTask, ProviderLog
from app.scheduler.jobs import start_scheduler
from app.services.monitor_service import run_check

app = FastAPI(title="Flight Price Monitor")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    if db.query(MonitorTask).count() == 0:
        db.add_all([
            MonitorTask(name="北京→武汉 周五晚", origin_city="北京", destination_city="武汉", weekday=4, time_start="18:00:00", time_end="23:59:59", max_price=500, enabled=True),
            MonitorTask(name="武汉→北京 周日晚", origin_city="武汉", destination_city="北京", weekday=6, time_start="18:00:00", time_end="23:59:59", max_price=500, enabled=True),
        ])
        db.commit()
    start_scheduler()


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "tasks": db.query(MonitorTask).count(), "alerts": db.query(Alert).count()})


@app.get("/tasks")
def tasks(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": db.query(MonitorTask).all()})


@app.get("/tasks/new")
def new_task(request: Request):
    return templates.TemplateResponse("task_form.html", {"request": request, "task": None})


@app.post("/tasks")
def create_task(name: str = Form(...), origin_city: str = Form(...), destination_city: str = Form(...), weekday: int = Form(...), time_start: str = Form(...), time_end: str = Form(...), max_price: int = Form(...), enabled: bool = Form(False), db: Session = Depends(get_db)):
    db.add(MonitorTask(name=name, origin_city=origin_city, destination_city=destination_city, weekday=weekday, time_start=time_start, time_end=time_end, max_price=max_price, enabled=enabled))
    db.commit()
    return RedirectResponse("/tasks", status_code=303)


@app.get("/tasks/{task_id}/edit")
def edit_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("task_form.html", {"request": request, "task": db.get(MonitorTask, task_id)})


@app.post("/tasks/{task_id}/update")
def update_task(task_id: int, name: str = Form(...), origin_city: str = Form(...), destination_city: str = Form(...), weekday: int = Form(...), time_start: str = Form(...), time_end: str = Form(...), max_price: int = Form(...), enabled: bool = Form(False), db: Session = Depends(get_db)):
    t = db.get(MonitorTask, task_id)
    t.name, t.origin_city, t.destination_city, t.weekday, t.time_start, t.time_end, t.max_price, t.enabled = name, origin_city, destination_city, weekday, time_start, time_end, max_price, enabled
    db.commit()
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{task_id}/delete")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.get(MonitorTask, task_id)
    db.delete(t)
    db.commit()
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{task_id}/run")
def run_now(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    run_check(db, task)
    return RedirectResponse("/results", status_code=303)


@app.get("/results")
def results(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("results.html", {"request": request, "rows": db.query(FlightPrice).order_by(FlightPrice.id.desc()).limit(200).all()})


@app.get("/history")
def history(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("history.html", {"request": request, "rows": db.query(FlightPrice).order_by(FlightPrice.id.desc()).limit(500).all()})


@app.get("/provider-logs")
def provider_logs(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("provider_logs.html", {"request": request, "rows": db.query(ProviderLog).order_by(ProviderLog.id.desc()).limit(500).all()})


@app.get("/settings")
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})
