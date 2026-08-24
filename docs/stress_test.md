# 压测说明

使用 Locust 对 FastAPI 后端进行负载测试。脚本路径：`scripts/locust_benchmark.py`。

登录仅在虚拟用户启动时执行一次（`on_start`），稳态百分位反映业务接口性能而非 PBKDF2 哈希开销。

## 覆盖接口

| 请求名 | 接口 | 说明 |
|--------|------|------|
| `auth.login` | `POST /api/v1/resident/auth/login` | 仅 `on_start` |
| `resident.list_orders` | `GET /api/v1/resident/work-orders` | 居民工单列表 |
| `resident.create_order` | `POST /api/v1/resident/work-orders` | 建单，`request_id` 防重复 |
| `admin.list_orders` | `GET /api/v1/admin/work-orders` | 管理端列表 |
| `admin.stats_overview` | `GET /api/v1/admin/stats/overview` | 统计概览（L1/L2 缓存） |
| `admin.dispatch` | `POST /api/v1/admin/work-orders/{id}/dispatch` | 智能派单 |
| `worker.list_assigned` | `GET /api/v1/worker/work-orders` | 工人任务箱 |
| `worker.performance` | `GET /api/v1/worker/personal/performance` | 绩效查询 |
| `worker.transition.*` | `POST /api/v1/worker/work-orders/{id}/status` | 状态流转 |
| `resident.rating` | `POST /api/v1/resident/work-orders/{id}/rating` | 评价闭环 |
| `health.ready` | `GET /health/ready` | 就绪探针 |

`closed_loop` 任务按 **创建 → 派单 → 接单 → 处理 → 回访 → 完成 → 评价** 走完一条工单。派单返回 409（无人可派）记为成功并提前结束该闭环，避免将业务容量耗尽误判为系统故障。

## 环境准备

先启动 API 服务：

```bash
uvicorn main:app --reload
```

压测前将限流调高，避免 429 干扰容量结论。在 `.env` 中设置：

```env
RATE_LIMIT_PER_MINUTE=100000
```

PostgreSQL 环境（可选）：

```powershell
docker compose -f deploy/docker-compose.yml up -d --build postgres redis rabbitmq minio api
```

## 运行命令

```powershell
# smoke：验证脚本与鉴权
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 5 -r 5 -t 30s --only-summary

# load：50 并发，3 分钟
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 50 -r 10 -t 3m --csv reports\load-50 --html reports\load-50.html

# stress：100 并发，3 分钟
.\.venv\Scripts\python.exe -m locust -f scripts\locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 100 -r 20 -t 3m --csv reports\load-100 --html reports\load-100.html
```

报告输出到 `reports/` 目录（`*.html` / `*.csv`），该目录不入库。

## 结果解读

- 按 Locust **请求名** 查看 P50/P95/P99 与失败率，不要只看总平均。
- `auth.login` 仅出现在用户启动阶段；对比 `resident.list_orders` / `resident.create_order` 评估业务接口延迟。
- `admin.stats_overview`、`worker.performance` 延迟下降表示缓存命中生效。
- `admin.dispatch` 返回 409 表示工人满载，属于业务约束而非 5xx 故障。
- `health.ready` 返回 503 表示数据库不可用。

记录压测环境：机器配置、Uvicorn Worker 数、数据库类型、并发数、持续时间、限流阈值，并保留原始 HTML/CSV 报告。
