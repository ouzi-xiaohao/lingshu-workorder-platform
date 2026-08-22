# 压测说明

当前脚本覆盖居民、工作人员、管理员三类流量，登录只在虚拟用户启动时发生一次，稳态百分位反映业务接口而不是 PBKDF2。

## 能测到什么

| 请求名 | 接口 | 说明 |
| --- | --- | --- |
| `auth.login` | `POST /api/v1/resident/auth/login` | 仅 `on_start`，观察 spawn 阶段 CPU |
| `resident.list_orders` | `GET /api/v1/resident/work-orders` | 读多路径 |
| `resident.create_order` | `POST /api/v1/resident/work-orders` | 规则分类建单，`request_id` 防重复 |
| `admin.list_orders` | `GET /api/v1/admin/work-orders` | 管理端列表 |
| `admin.stats_overview` | `GET /api/v1/admin/stats/overview` | L1/L2 缓存命中 |
| `admin.dispatch` | `POST /api/v1/admin/work-orders/{id}/dispatch` | 调度锁、工人负载 |
| `worker.list_assigned` | `GET /api/v1/worker/work-orders` | 工人任务箱 |
| `worker.performance` | `GET /api/v1/worker/personal/performance` | 绩效缓存 |
| `worker.transition.*` | `POST /api/v1/worker/work-orders/{id}/status` | 状态机 |
| `resident.rating` | `POST /api/v1/resident/work-orders/{id}/rating` | 闭环评价 |
| `health.ready` | `GET /health/ready` | 就绪探针 |

`closed_loop` 任务按 创建 → 派单 → 接单/处理/回访/完成 → 评价 走完一条工单。派单返回 409（无人可派）记为成功但提前结束该闭环，避免把业务容量打满当成系统故障。

## 测不到什么

- 真实 Whisper / YOLO（默认 `AI_MODE=fallback`）
- 附件上传与 MinIO
- Celery 巡检
- 前端 Sites / D1

## 运行

先起 API，开发环境把限流调高，避免 429 干扰容量结论：

```env
RATE_LIMIT_PER_MINUTE=100000
```

```powershell
# smoke：脚本与鉴权是否通
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 5 -r 5 -t 30s --only-summary

# load：观察 P95 / 错误率
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 50 -r 10 -t 3m --csv reports\load-50 --html reports\load-50.html

# stress：找饱和点
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 100 -r 20 -t 3m --csv reports\load-100 --html reports\load-100.html
```

PostgreSQL 环境：

```powershell
docker compose -f deploy/docker-compose.yml up -d --build postgres redis rabbitmq minio api
```

## 如何读结果

- 看 Locust 按 **请求名** 拆开的 P50/P95/P99 和失败率，不要只用总平均。
- `auth.login` 只出现在用户启动阶段；对比它和 `resident.list_orders` / `resident.create_order`，避免再把哈希登录算进业务 P95。
- `admin.stats_overview`、`worker.performance` 变快说明缓存生效；`admin.dispatch` 409 增多说明工人满载，不是 5xx。
- `health.ready` 变 503 说明数据库已不可用。

## 目标（设计值，不是已实测结论）

| 接口 | P95 目标 | 错误率目标 |
| --- | ---: | ---: |
| 创建工单 | < 300ms（不含真实 AI） | < 0.1% |
| 工单列表 | < 100ms | < 0.1% |
| 智能派单 | < 150ms | < 0.1% |
| 统计概览 | < 50ms（缓存命中） | < 0.1% |

写报告时记录：机器配置、Worker 数、数据库、并发模型、时长、限流阈值、原始 HTML/CSV。`reports/` 只作本地输出目录，不要把 HTML/CSV 提交进仓库。
