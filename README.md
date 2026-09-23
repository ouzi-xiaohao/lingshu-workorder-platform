# 灵枢 · 多模态智能工单协同调度平台

面向园区、社区和设施运维场景的智能工单平台。系统支持文字、图片、音频和视频报修，通过多模态信息提取、意图识别、Agent 调度、状态机流转和评价积分完成工单闭环。

项目同时提供两种运行形态：

- **在线演示形态**：React/Vinext 前端通过 `/api/platform` 访问服务端接口，使用 Cloudflare D1 保存业务数据、R2 保存附件。
- **企业自部署形态**：FastAPI 提供领域 API，使用 PostgreSQL、Redis、RabbitMQ、Celery、MinIO 和 Nginx 组成完整后端基础设施。

> 默认开发配置使用 SQLite、本地附件目录和规则降级模式，无需 GPU 或外部中间件即可启动 FastAPI。

## Demo 运行图

### 角色入口

![身份选择页面](./docs/images/demo-role-selection.png)

管理员演示账号可以切换居民、工作人员和运营管理员视角；普通账号仅能进入自身角色工作台。

### 居民端

| 多模态报修入口 | 工单提交与附件上传 |
| --- | --- |
| ![居民多模态报修](./docs/images/demo-resident-report.png) | ![居民提交工单](./docs/images/demo-resident-create-order.png) |

![居民服务评价](./docs/images/demo-resident-rating.png)

- 支持图片、语音、视频、文字及组合附件报修。
- 提交时可选择分类、紧急程度和发生区域，也可交由 AI 自动识别。
- 工单完成后进入服务评价页面，评价结果用于服务质量闭环。

### 工作人员端

| 我的任务与状态流转 | 积分绩效 |
| --- | --- |
| ![工作人员任务中心](./docs/images/demo-worker-tasks.png) | ![工作人员积分绩效](./docs/images/demo-worker-performance.png) |

- 仅展示智能调度分配给当前工作人员的任务。
- 支持接单、处理中、待回访、已完成等状态迁移。
- 展示积分、完成量、按时率、满意度、当前负载和积分规则。

### 管理员端

| 指挥中心 | 工单中心 |
| --- | --- |
| ![管理员指挥中心](./docs/images/demo-admin-dashboard.png) | ![管理员工单中心](./docs/images/demo-admin-orders.png) |

| 人员调度 | 智能体运行面板 |
| --- | --- |
| ![人员调度](./docs/images/demo-admin-workforce.png) | ![智能体运行面板](./docs/images/demo-admin-agents.png) |

- 指挥中心汇总工单指标、协同流水线、人员负载、最近工单和智能预警。
- 工单中心集中展示识别结果、优先级、处理人、AI 摘要和状态轨迹。
- 人员调度展示技能、覆盖区域、当前容量和服务评分。
- 智能体面板展示多模态融合、意图识别、智能调度、流转监控和积分结算组件。

## 核心能力

- **多角色协同**：居民、工作人员、管理员三级 RBAC，资源归属与操作权限双重校验。
- **多模态报修**：支持图片、音频、视频上传，提供格式、大小、归属和安全路径校验。
- **智能识别**：可接入 Whisper、YOLO 与大模型服务，输出标准化摘要、类别、优先级、标签和置信度。
- **Agent 调度**：采用 Plan–Act–Evaluate 模式，动态选择本区专业、跨区专业和综合人员兜底策略。
- **可解释派单**：综合技能、负载、距离和历史评分排序，记录策略、权重、候选方案、置信度及决策轨迹。
- **全生命周期**：覆盖创建、派单、接单、处理、回访、完成、取消、评价与积分流水。
- **高可用设计**：提供多级缓存、分布式锁、限流、熔断、主备模型、规则兜底和异步补偿扫描。
- **可观测性**：统一 Trace ID、结构化日志、事件审计、健康检查和依赖熔断状态查询。

## 系统架构

```mermaid
flowchart TB
    subgraph Client[访问端]
        Resident[居民端]
        Worker[工作人员端]
        Admin[管理端]
    end

    subgraph Web[交互层]
        UI[React 19 + Vinext]
        OnlineAPI[Platform API]
    end

    subgraph Gateway[接入层]
        Nginx[Nginx]
        FastAPI[FastAPI API]
        Middleware[JWT / RBAC / Trace / Rate Limit]
    end

    subgraph Domain[领域层]
        Service[Application Service]
        Engine[AgentEngine / AgentHub]
        Intent[Intent Agent]
        Dispatch[Dispatch Agent]
        Flow[Flow Agent]
        Credit[Credit Agent]
        Patrol[Patrol Agent]
        Toolkit[筛选 / 距离 / 评分工具]
        DAO[DAO + SQLAlchemy]
    end

    subgraph Async[异步任务]
        RabbitMQ[RabbitMQ]
        Celery[Celery Worker / Beat]
    end

    subgraph Infra[数据与基础设施]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        MinIO[(MinIO)]
        AI[Whisper / YOLO / LLM]
        D1[(Cloudflare D1)]
        R2[(Cloudflare R2)]
    end

    Resident --> UI
    Worker --> UI
    Admin --> UI
    UI --> OnlineAPI
    OnlineAPI --> D1
    OnlineAPI --> R2

    Resident -. 企业自部署 .-> Nginx
    Worker -. 企业自部署 .-> Nginx
    Admin -. 企业自部署 .-> Nginx
    Nginx --> FastAPI --> Middleware --> Service
    Service --> Engine
    Engine --> Intent
    Engine --> Dispatch
    Engine --> Flow
    Engine --> Credit
    Engine --> Patrol
    Dispatch --> Toolkit
    Service --> DAO --> PostgreSQL
    Service --> Redis
    Service --> MinIO
    Service --> RabbitMQ --> Celery
    Celery --> AI
    Celery --> PostgreSQL
    Celery --> MinIO
```

### 分层职责

| 层级 | 目录 | 职责 |
| --- | --- | --- |
| API 层 | `src/api` | 路由、鉴权、参数校验与响应转换 |
| Service 层 | `src/service` | 用例编排、事务边界、幂等与缓存失效 |
| Agent 层 | `src/agent` | 意图识别、调度规划、状态校验、积分及巡检决策 |
| AI 层 | `src/ai_services` | 语音转写、视觉检测、大模型摘要与多模态融合 |
| DAO 层 | `src/dao` | 数据查询与持久化操作封装 |
| Model/Schema | `src/models`、`src/schemas` | ORM 模型、请求与响应契约 |
| 基础设施层 | `src/extensions`、`src/common` | PostgreSQL、Redis、MinIO、缓存、锁、熔断、日志和追踪 |
| 异步任务层 | `src/tasks` | AI 富化、失败重试、定时巡检与积压任务捞回 |

依赖方向遵循 `API → Service → Agent/DAO → Infrastructure`。Agent 只输出决策，不直接修改数据库；锁、状态变更、负载更新和事件记录由 Service 在事务内完成。

## 核心业务链路

```mermaid
sequenceDiagram
    actor U as 居民
    participant API as FastAPI
    participant S as WorkOrderService
    participant M as 多模态服务
    participant A as Intent Agent
    participant DB as PostgreSQL
    participant MQ as RabbitMQ/Celery
    participant D as Dispatch Agent
    participant W as 工作人员

    U->>API: 上传附件并提交工单
    API->>S: 校验身份、参数与附件归属
    S->>M: 轻量融合
    M-->>S: 标准化文本与证据
    S->>A: 分类、优先级、置信度
    A-->>S: 初步识别结果
    S->>DB: 工单 + 创建事件（同一事务）
    S-->>MQ: 投递重度 AI 富化任务
    API-->>U: 返回已创建工单
    D->>D: Plan → Act → Evaluate
    D-->>S: 处理人、策略、得分与决策轨迹
    S->>DB: 派单、负载与审计事件（同一事务）
    W->>API: 接单、处理、回访、完成
    API->>DB: 状态机校验并记录事件
```

### Agent 调度机制

调度 Agent 围绕“找到安全且合适的处理人”执行受约束的 Plan–Act–Evaluate 循环：

1. **Plan**：根据工单类别、优先级、区域和风险生成策略序列。
2. **Act**：调用候选人筛选、Haversine 距离和可解释评分工具。
3. **Evaluate**：有合格人员则输出决策；无候选人则切换下一策略。
4. **Escalate**：高风险工单不存在合格人员时停止自动派单并转人工。

普通工单采用技能 45%、负载 25%、距离 20%、评分 10% 的均衡权重；紧急工单提高距离权重，优先缩短响应时间。评分只是 Agent 的确定性工具，人员容量、状态机和事务约束不会交由模型绕过。

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 前端 | React 19、TypeScript、Vinext、Vite、Tailwind CSS |
| API | Python 3.12、FastAPI、Pydantic、SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 16、SQLite（开发）、Cloudflare D1（在线） |
| 缓存与协调 | Redis、L1 TTL Cache、Pub/Sub、分布式锁 |
| 消息与任务 | RabbitMQ、Celery Worker、Celery Beat |
| 对象存储 | MinIO、本地受控目录、Cloudflare R2 |
| AI | Faster Whisper、YOLO、可配置主备 LLM |
| 工程化 | Docker Compose、Nginx、Pytest、Locust、GitHub Actions |

## 目录结构

```text
.
├── app/                         # React/Vinext 页面与 Platform API
├── db/                          # 在线数据库定义
├── drizzle/                     # D1 数据库迁移
├── deploy/                      # Docker、Compose、Nginx 与 CI
├── docs/                        # 架构、压测和 Demo 图片
├── public/                      # 前端静态资源
├── scripts/                     # 初始化与 Locust 压测脚本
├── src/
│   ├── agent/                   # AgentEngine、业务 Agent 与调度工具
│   ├── ai_services/             # STT、视觉、LLM 与多模态融合
│   ├── api/v1/                  # resident / worker / admin API
│   ├── common/                  # 缓存、熔断、锁、日志、追踪
│   ├── core/                    # 配置、安全、错误码与异常
│   ├── dao/                     # 数据访问层
│   ├── extensions/              # PostgreSQL、Redis、MinIO 客户端
│   ├── middleware/              # Trace、访问日志与限流
│   ├── models/                  # SQLAlchemy ORM
│   ├── schemas/                 # Pydantic 请求与响应模型
│   ├── service/                 # 业务服务与事务边界
│   └── tasks/                   # Celery 异步与定时任务
├── tests/                       # API、Service、Agent 测试
├── main.py                      # FastAPI 入口
├── package.json                 # 前端依赖与命令
└── requirements.txt             # 后端依赖
```

## 快速开始

### 1. 启动前端 Demo

环境要求：Node.js `>= 22.13`、pnpm。

```bash
pnpm install
pnpm dev
```

访问 <http://localhost:3000>。本地开发由 Miniflare 提供 D1/R2 兼容资源，前端通过 `/api/platform` 读写服务端数据。

### 2. 启动 FastAPI 后端

环境要求：Python `>= 3.12`。

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/init_test_data.py
uvicorn main:app --reload
```

Linux/macOS：

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_test_data.py
uvicorn main:app --reload
```

启动后可访问：

- API 文档：<http://localhost:8000/docs>
- 存活探针：<http://localhost:8000/health>
- 就绪探针：<http://localhost:8000/health/ready>

### 3. 启动完整后端基础设施

```bash
docker compose -f deploy/docker-compose.yml up --build
```

默认端口：

| 服务 | 地址 |
| --- | --- |
| Nginx/API | <http://localhost:8080> |
| FastAPI | <http://localhost:8000> |
| RabbitMQ 管理台 | <http://localhost:15672> |
| MinIO API | <http://localhost:9000> |
| MinIO Console | <http://localhost:9001> |

> Compose 负责编排 FastAPI 及后端依赖；前端仍通过 `pnpm dev` 单独启动。

## 演示账号

| 角色 | 用户名 | 密码 | 权限范围 |
| --- | --- | --- | --- |
| 居民 | `resident` | `resident123` | 创建、查看、取消和评价本人工单 |
| 工作人员 | `worker` | `worker123` | 查看本人任务、推进状态和查询绩效 |
| 管理员 | `admin` | `admin123` | 全局查询、派单、改派、督办与系统管理 |

演示账号只用于本地开发。生产环境启动时会校验数据库类型和 `SECRET_KEY`，禁止使用默认不安全配置。

## 关键配置

复制 `.env.example` 为 `.env`，按运行环境修改：

| 变量 | 默认值/示例 | 说明 |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | 运行环境；生产环境启用安全配置校验 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/lingshu.db` | 数据库连接地址 |
| `REDIS_URL` | `redis://localhost:6379/0` | 缓存、锁、限流与任务结果后端 |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | Celery Broker |
| `MEDIA_STORAGE_MODE` | `auto` | `auto`、`local` 或 `minio` |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO 服务地址 |
| `AI_MODE` | `fallback` | `fallback`、`local` 或 `production` |
| `AI_ASYNC_ENABLED` | `true` | 是否异步执行多模态富化 |
| `LLM_API_URL` | 空 | 主模型服务地址 |
| `LLM_FALLBACK_API_URL` | 空 | 备用模型服务地址 |

启用本地 Whisper/YOLO：

```bash
pip install -r requirements-ai.txt
```

```env
AI_MODE=local
WHISPER_MODEL=base
YOLO_MODEL=yolov8n.pt
```

## API 示例

FastAPI 附件与工单采用两阶段提交：先上传附件取得 `object_key`，再创建工单。

```text
POST /api/v1/resident/auth/login
POST /api/v1/resident/media
POST /api/v1/resident/work-orders
POST /api/v1/admin/work-orders/{id}/dispatch
POST /api/v1/worker/work-orders/{id}/status
POST /api/v1/resident/work-orders/{id}/rating
GET  /health/ready
```

## 测试与质量检查

```bash
python -m pytest -q
pnpm lint
pnpm build
```

Locust 压测示例：

```bash
python -m locust -f scripts/locust_benchmark.py \
  --host http://127.0.0.1:8000 \
  --headless -u 50 -r 10 -t 3m
```

压测指标、目标和结果解读见 [`docs/stress_test.md`](./docs/stress_test.md)。

## 容错策略

| 故障依赖 | 系统行为 |
| --- | --- |
| 主 LLM | 切换备用模型；仍失败则使用规则摘要 |
| Whisper/YOLO | 熔断并保留文本或文件名证据 |
| Redis | 缓存回源数据库，锁和限流降级为单实例本地实现 |
| RabbitMQ | 同步建单保持可用，定时任务扫描并重新投递待富化工单 |
| MinIO | `auto` 模式降级至本地受控目录；强制模式返回 503 |
| PostgreSQL | 就绪探针返回 503，实例停止接收业务流量 |

## 文档

- [系统架构与设计边界](./docs/architecture.md)
- [压测方案与指标说明](./docs/stress_test.md)
