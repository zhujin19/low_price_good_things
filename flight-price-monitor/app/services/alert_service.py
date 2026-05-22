from app.models.alert import Alert


def create_alert(db, task_id: int, flight_price_id: int, message: str):
    db.add(Alert(task_id=task_id, flight_price_id=flight_price_id, message=message))
    db.commit()
