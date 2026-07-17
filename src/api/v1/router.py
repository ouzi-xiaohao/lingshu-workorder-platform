from fastapi import APIRouter

from src.api.v1.admin import order_manage, stats, system, user_manage
from src.api.v1.resident import auth, user, work_order
from src.api.v1.worker import order_handle, personal


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/resident/auth", tags=["居民-认证"])
api_router.include_router(work_order.router, prefix="/resident/work-orders", tags=["居民-工单"])
api_router.include_router(user.router, prefix="/resident/user", tags=["居民-个人中心"])
api_router.include_router(order_handle.router, prefix="/worker/work-orders", tags=["工作人员-工单处理"])
api_router.include_router(personal.router, prefix="/worker/personal", tags=["工作人员-个人绩效"])
api_router.include_router(order_manage.router, prefix="/admin/work-orders", tags=["管理端-工单管理"])
api_router.include_router(user_manage.router, prefix="/admin/users", tags=["管理端-用户管理"])
api_router.include_router(stats.router, prefix="/admin/stats", tags=["管理端-数据统计"])
api_router.include_router(system.router, prefix="/admin/system", tags=["管理端-系统配置"])
