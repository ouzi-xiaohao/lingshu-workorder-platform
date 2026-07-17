from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent_engine import WorkerCandidate, choose_worker, classify_intent
from .store import WorkOrderStore


store = WorkOrderStore(str(Path(__file__).parents[1] / "data" / "lingshu.db"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield


app = FastAPI(title="灵枢智能工单 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])


class WorkOrderCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=2000)
    area: str = Field(min_length=2, max_length=80)
    reporter: str = Field(default="匿名用户", max_length=60)
    longitude: float = 121.4737
    latitude: float = 31.2304
    attachments: list[str] = Field(default_factory=list, max_length=10)


WORKERS = [
    WorkerCandidate("w-001", "陈立", "设备故障/机电维修", 121.475, 31.232, 3, 5, 98),
    WorkerCandidate("w-002", "赵诚", "照明设施/电气照明", 121.468, 31.229, 2, 4, 96),
    WorkerCandidate("w-003", "孙航", "安全隐患/消防安全", 121.479, 31.226, 3, 4, 95),
    WorkerCandidate("w-004", "李昂", "暖通空调/智能终端", 121.471, 31.234, 1, 4, 93),
]


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or uuid4().hex
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "lingshu-api"}


@app.get("/api/v1/work-orders")
async def list_work_orders(status: str | None = Query(default=None)):
    return {"items": store.list(status), "total": len(store.list(status))}


@app.post("/api/v1/work-orders", status_code=202)
async def create_work_order(payload: WorkOrderCreate, request: Request, idempotency_key: str | None = Header(default=None)):
    work_order_id = f"WO-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}"
    intent = classify_intent(f"{payload.title} {payload.description}")
    item = {
        "id": work_order_id, "title": payload.title, "description": payload.description,
        "category": intent["category"], "area": payload.area, "priority": intent["priority"],
        "status": "待派单", "reporter": payload.reporter, "assignee": "",
        "confidence": intent["confidence"], "attachments": payload.attachments,
        "trace_id": request.state.trace_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store.create(item)
    return {"data": item, "task_id": idempotency_key or uuid4().hex, "message": "已进入智能调度队列"}


@app.get("/api/v1/work-orders/{work_order_id}")
async def get_work_order(work_order_id: str):
    item = store.get(work_order_id)
    if not item:
        raise HTTPException(404, "工单不存在")
    return {"data": item}


@app.post("/api/v1/work-orders/{work_order_id}/dispatch")
async def dispatch_work_order(work_order_id: str):
    item = store.get(work_order_id)
    if not item:
        raise HTTPException(404, "工单不存在")
    if item.get("assignee"):
        return {"data": item, "message": "该工单已完成派单"}
    decision = choose_worker(str(item["category"]), 121.4737, 31.2304, WORKERS)
    if not decision:
        raise HTTPException(409, "暂无可调度人员")
    updated = store.assign(work_order_id, str(decision["worker_name"]))
    return {"data": updated, "decision": decision}
