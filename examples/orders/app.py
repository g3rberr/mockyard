import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Orders Service", version="1.0.0")

store: dict[str, dict] = {}


class OrderItem(BaseModel):
    productId: str
    quantity: int
    price: float


class CreateOrder(BaseModel):
    userId: str
    items: list[OrderItem]


class Order(BaseModel):
    id: str
    userId: str
    total: float
    status: str
    createdAt: str


@app.get("/orders")
def list_orders(limit: Optional[int] = None):
    items = list(store.values())
    if limit:
        items = items[:limit]
    return items


@app.post("/orders", status_code=201)
def create_order(body: CreateOrder):
    order_id = uuid.uuid4().hex[:12]
    total = sum(item.price * item.quantity for item in body.items)
    order = Order(
        id=order_id,
        userId=body.userId,
        total=total,
        status="pending",
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    store[order_id] = order.model_dump()
    return store[order_id]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = store.get(order_id)
    if not order:
        raise HTTPException(404)
    return order
