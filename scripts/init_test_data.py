import asyncio
from uuid import uuid4

from src.extensions.postgres import AsyncSessionLocal, init_db
from src.schemas.request.work_order import WorkOrderCreate
from src.service.user_service import ensure_bootstrap_users
from src.service.work_order_service import WorkOrderService
from src.dao.user_dao import UserDAO


SAMPLES = [
    ("A3 栋地下车库排水泵异响", "排水泵持续异响并伴随少量积水", "东区 · A3"),
    ("园区北门路灯连续闪烁", "北门入口三盏路灯从昨晚开始连续闪烁", "北区 · 1 号门"),
    ("B2 办公区空调不制冷", "会议室空调无法制冷，室温持续升高", "西区 · B2"),
]


async def main():
    await init_db()
    await ensure_bootstrap_users()
    async with AsyncSessionLocal() as session:
        resident = await UserDAO(session).get_by_username("resident")
        for title, description, area in SAMPLES:
            await WorkOrderService(session).create(WorkOrderCreate(title=title, description=description, area=area, request_id=f"seed-{uuid4().hex}"), resident.id, uuid4().hex)
    print(f"initialized {len(SAMPLES)} work orders")


if __name__ == "__main__":
    asyncio.run(main())
