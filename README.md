# 灵枢 · 多模态智能工单协同调度平台

本项目按照《多模态智能工单协同调度平台》设计实现，包含可交互运营前端，以及按企业级 FastAPI 规范拆分的后端。开发环境无需中间件即可使用 SQLite 启动；生产适配覆盖 PostgreSQL、Redis、RabbitMQ、MinIO、Celery 与 Nginx。

## 目录结构

```text
├── main.py                    # FastAPI 入口
├── app/                       # React/Vinext 运营前端
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

访问 `http://localhost:3000`。现有前端包含完整演示交互，后续可按 `NEXT_PUBLIC_API_BASE_URL` 逐步切换到真实接口。

## 完整基础设施

```bash
copy .env.example .env
docker compose -f deploy/docker-compose.yml up --build
```

详见 [系统架构](docs/architecture.md) 和 [压测说明](docs/stress_test.md)。
