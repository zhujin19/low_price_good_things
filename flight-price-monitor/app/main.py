from collections import defaultdict
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Alert, FlightPrice, MonitorTask, ProviderLog
from app.paths import APP_DIR
from app.scheduler.jobs import start_scheduler
from app.services.monitor_service import run_check
from app.services.time_service import format_beijing

app = FastAPI(title="Flight Price Monitor")
BASE_DIR = APP_DIR
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["beijing_time"] = format_beijing


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
def dashboard(
    request: Request,
    tab: str = Query(default="overview"),
    low_price_sort: str = Query(default="latest"),
    db: Session = Depends(get_db),
):
    tasks = db.query(MonitorTask).order_by(MonitorTask.id.desc()).all()
    results = db.query(FlightPrice).order_by(*_result_order_by(low_price_sort)).limit(200).all()
    history_rows = db.query(FlightPrice).order_by(FlightPrice.id.desc()).limit(500).all()
    logs = db.query(ProviderLog).order_by(ProviderLog.id.desc()).limit(500).all()
    top_rows = _global_top_rows(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "tab": tab,
        "low_price_sort": low_price_sort,
        "tasks_count": len(tasks),
        "alerts_count": db.query(Alert).count(),
        "tasks": tasks,
        "task_top_prices": _task_top_prices(db, tasks),
        "results": results,
        "top_ranks": _row_top_ranks(top_rows),
        "history_rows": history_rows,
        "logs": logs,
    })


@app.get("/tasks")
def tasks(request: Request, db: Session = Depends(get_db)):
    task_rows = db.query(MonitorTask).order_by(MonitorTask.id.desc()).all()
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "tasks": task_rows,
            "task_top_prices": _task_top_prices(db, task_rows),
        },
    )


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


@app.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int, enabled: bool = Form(False), db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    task.enabled = enabled
    db.commit()
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{task_id}/run")
def run_now(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    saved_count = run_check(db, task)
    task_name = quote(task.name)
    return RedirectResponse(
        f"/results?notice=run_complete&task_name={task_name}&saved_count={saved_count}",
        status_code=303,
    )


@app.get("/results")
def results(
    request: Request,
    sort: str = Query(default="latest"),
    notice: str | None = Query(default=None),
    task_name: str | None = Query(default=None),
    saved_count: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = db.query(FlightPrice).order_by(FlightPrice.id.desc()).limit(1000).all()
    groups = _price_groups(rows, sort)
    toast_message = None
    if notice == "run_complete" and task_name is not None and saved_count is not None:
        if saved_count > 0:
            toast_message = f"「{task_name}」检测完成，新增 {saved_count} 条低价票记录。"
        else:
            toast_message = (
                f"「{task_name}」检测完成，未新增低价票。"
                "可能是未命中阈值、携程暂无价格，或相同低价已记录；可查看采集日志。"
            )
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "groups": groups,
            "sort": sort,
            "toast_message": toast_message,
        },
    )


@app.get("/history")
def history(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("history.html", {"request": request, "rows": db.query(FlightPrice).order_by(FlightPrice.id.desc()).limit(500).all()})


@app.get("/provider-logs")
def provider_logs(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("provider_logs.html", {"request": request, "rows": db.query(ProviderLog).order_by(ProviderLog.id.desc()).limit(500).all()})


@app.get("/settings")
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


def _result_order_by(sort: str):
    return {
        "price_desc": [desc(FlightPrice.adult_price), desc(FlightPrice.id)],
        "price_asc": [FlightPrice.adult_price.asc(), desc(FlightPrice.id)],
        "latest": [desc(FlightPrice.id)],
    }.get(sort, [desc(FlightPrice.id)])


def _global_top_rows(db: Session, limit: int = 3) -> list[FlightPrice]:
    return (
        db.query(FlightPrice)
        .order_by(FlightPrice.adult_price.asc(), desc(FlightPrice.id))
        .limit(limit)
        .all()
    )


def _row_top_ranks(rows: list[FlightPrice]) -> dict[int, int]:
    return {row.id: index + 1 for index, row in enumerate(rows)}


def _task_top_prices(db: Session, tasks: list[MonitorTask]) -> dict[int, list[FlightPrice]]:
    top_prices: dict[int, list[FlightPrice]] = {}
    for task in tasks:
        top_prices[task.id] = (
            db.query(FlightPrice)
            .filter(FlightPrice.task_id == task.id)
            .order_by(FlightPrice.adult_price.asc(), desc(FlightPrice.id))
            .limit(3)
            .all()
        )
    return top_prices


def _price_groups(rows: list[FlightPrice], sort: str) -> list[dict]:
    grouped_rows: dict[tuple, list[FlightPrice]] = defaultdict(list)
    for row in rows:
        grouped_rows[
            (
                row.target_date,
                row.flight_no,
                row.depart_airport,
                row.arrive_airport,
            )
        ].append(row)

    groups = []
    for key, group_rows in grouped_rows.items():
        ordered_rows = sorted(group_rows, key=lambda item: (item.created_at, item.id))
        min_row = min(ordered_rows, key=lambda item: (item.adult_price, -item.id))
        latest_row = max(ordered_rows, key=lambda item: (item.created_at, item.id))
        target_date, flight_no, depart_airport, arrive_airport = key
        groups.append(
            {
                "key": "|".join(
                    [
                        target_date.isoformat(),
                        flight_no,
                        depart_airport,
                        arrive_airport,
                    ]
                ),
                "target_date": target_date,
                "flight_no": flight_no,
                "route": f"{depart_airport}→{arrive_airport}",
                "airline": latest_row.airline,
                "providers": "、".join(sorted({row.provider for row in ordered_rows})),
                "depart_time": latest_row.depart_time,
                "arrive_time": latest_row.arrive_time,
                "latest_row": latest_row,
                "latest_price": latest_row.adult_price,
                "latest_created_at": latest_row.created_at,
                "min_row": min_row,
                "min_price": min_row.adult_price,
                "min_created_at": min_row.created_at,
                "rows": ordered_rows,
                "chart": _price_chart(ordered_rows),
            }
        )

    top_keys = [
        group["key"]
        for group in sorted(groups, key=lambda item: (item["min_price"], -item["min_row"].id))[:3]
    ]
    top_ranks = {key: index + 1 for index, key in enumerate(top_keys)}
    for group in groups:
        group["top_rank"] = top_ranks.get(group["key"])

    if sort == "price_asc":
        return sorted(groups, key=lambda item: (item["min_price"], -item["latest_row"].id))
    if sort == "price_desc":
        return sorted(groups, key=lambda item: (-item["min_price"], -item["latest_row"].id))
    return sorted(groups, key=lambda item: (item["latest_created_at"], item["latest_row"].id), reverse=True)


def _price_chart(rows: list[FlightPrice]) -> dict:
    width = 240
    height = 72
    padding = 12
    prices = [row.adult_price for row in rows]
    min_price = min(prices)
    max_price = max(prices)
    price_range = max(max_price - min_price, 1)
    x_range = max(len(rows) - 1, 1)
    points = []
    min_point = None
    min_index = prices.index(min_price)

    for index, row in enumerate(rows):
        x = padding + ((width - padding * 2) * index / x_range if len(rows) > 1 else (width - padding * 2) / 2)
        y = padding + (max_price - row.adult_price) * (height - padding * 2) / price_range
        point = {
            "x": round(x, 1),
            "y": round(y, 1),
            "price": row.adult_price,
            "time": format_beijing(row.created_at, "%m-%d %H:%M"),
        }
        points.append(point)
        if index == min_index:
            min_point = point

    return {
        "width": width,
        "height": height,
        "points": " ".join(f"{point['x']},{point['y']}" for point in points),
        "point_items": points,
        "min_point": min_point,
        "min_price": min_price,
        "max_price": max_price,
    }
