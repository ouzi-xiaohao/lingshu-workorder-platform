# 灵枢 · 多模态智能工单协同调度平台

根据《多模态智能工单协同调度平台》项目设计实现的可运行演示版。项目保留了文档中的多智能体协同、全生命周期工单管理、智能派单、人员负载和统计分析，并将默认运行依赖收敛为浏览器端演示 + FastAPI + SQLite，便于快速启动与面试展示。

## 已实现

- 指挥中心：关键指标、Agent 流水线、SLA 关注列表、人员负载与智能预警
- 工单池：搜索筛选、详情、AI 多模态摘要、决策链、智能派单
- 智能体中心：意图识别、调度、流转、积分、巡检五类 Agent 状态
- 人员调度：技能、区域、容量、绩效与实时可用状态
- 数据分析：趋势、分类占比、响应时长、一次解决率与满意度
- 新建工单：文字与附件入口、AI 任务队列反馈
- FastAPI：工单创建/查询/派单、SQLite 持久化、幂等键、trace_id、CORS
- 调度引擎：规则意图识别 + 技能/负载/距离/评分加权决策

## 本地运行

前端要求 Node.js 22+：

```bash
pnpm install
pnpm dev
```

访问 `http://localhost:3000`。

后端要求 Python 3.12+：

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API 文档位于 `http://localhost:8000/docs`。当前前端包含完整演示数据与交互，可独立运行；对接后端时可将工单状态替换为 `/api/v1/work-orders` 响应。

## 架构取舍

文档中的 PostgreSQL、Redis、RabbitMQ、MinIO、Celery 适合生产环境，但会显著增加首次启动成本。本版本用 SQLite 与同步 API 跑通业务闭环，并保留清晰的 Agent 与数据访问边界。生产化时可将 Store 替换为 PostgreSQL、将创建后的分析与派单任务投递到 RabbitMQ/Celery，并使用 Redis 实现分布式锁、限流和幂等缓存。
