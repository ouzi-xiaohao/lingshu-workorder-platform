# 灵枢 · 多模态智能工单协同调度平台

本项目按照《多模态智能工单协同调度平台》设计实现，包含可交互运营前端、Sites 在线持久化接口，以及按企业级 FastAPI 规范拆分的后端。开发环境无需中间件即可使用 SQLite 与本地附件目录启动；生产适配覆盖 PostgreSQL、Redis、RabbitMQ、MinIO、Celery 与 Nginx。

## 已实现功能

- ChatGPT 工作区身份识别，以及 FastAPI 居民、工作人员、管理员三类账号权限。
- 图片、音频、视频上传；格式、大小与归属校验；R2、MinIO、本地目录三种存储路径。
- 工单创建、查询、取消、智能派单、接单、处理、回访、完成与评价。
- 多模态融合、规则兜底分类、Whisper 与 YOLO 可选本地模型适配。
- 技能、区域、负载、评分综合调度，完整事件轨迹与处理人负载更新。
- 在线 D1 持久化、R2 附件存储；本地 SQLite/PostgreSQL 业务存储。
- 流转状态机、积分服务、统计、限流、链路追踪、结构化日志和自动化测试。

## 目录结构

```text
├── main.py                    # FastAPI 入口
├── app/                       # React/Vinext 运营前端
├── app/api/platform/          # 在线 D1/R2 业务接口
├── db/、drizzle/              # 在线数据库模型与迁移
├── deploy/                    # Docker Compose、Dockerfile、Nginx、CI
├── docs/                      # 架构与压测说明
├── scripts/                   # 初始化数据、压测、雪花 ID 测试
├── src/
│   ├── api/v1/                # resident / worker / admin 三类接口域
│   ├── service/               # 工单、调度、积分、用户、统计服务
│   ├── dao/                   # 数据访问层
│   ├── models/                # SQLAlchemy 2.0 ORM
│   ├── schemas/               # Pydantic 请求与响应模型
│   ├── core/                  # 配置、安全、异常、错误码
│   ├── common/                # ID、地理计算、日志、协调锁
│   ├── middleware/            # trace、访问日志、限流
│   ├── extensions/            # PostgreSQL、Redis、RabbitMQ、MinIO
│   ├── agent/                 # 五类 Agent、状态中心、调度器
│   ├── ai_services/           # LLM、语音、图像、多模态融合适配
│   └── tasks/                 # Celery 异步与定时任务
└── tests/                     # API、Service、Agent 测试
```

## 后端运行

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
python scripts/init_test_data.py
uvicorn main:app --reload
```

如需启用本地真实语音转写和图像/视频目标检测，安装扩展依赖并修改 `.env`：

```bash
pip install -r requirements-ai.txt
```

```env
AI_MODE=local
WHISPER_MODEL=base
YOLO_MODEL=yolov8n.pt
```

默认 `AI_MODE=fallback` 使用轻量规则分析，保证没有 GPU 和大型模型时业务仍可完整运行。

打开 `http://localhost:8000/docs` 查看 API 文档。内置演示账号：

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 居民 | resident | resident123 |
| 工作人员 | worker | worker123 |
| 管理员 | admin | admin123 |

## 前端运行

```bash
pnpm install
pnpm dev
```

访问 `http://localhost:3000`。前端直接调用 `/api/platform`，本地由 Miniflare 提供 D1/R2，在线由 Sites 提供对应持久化资源；不再使用浏览器内演示数据。

FastAPI 的附件上传接口为 `POST /api/v1/resident/media`，先上传文件取得 `object_key`，再将返回的附件元数据传给 `POST /api/v1/resident/work-orders`。

## 完整基础设施

```bash
copy .env.example .env
docker compose -f deploy/docker-compose.yml up --build
```

详见 [系统架构](docs/architecture.md) 和 [压测说明](docs/stress_test.md)。
