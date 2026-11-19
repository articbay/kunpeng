# Kunpeng 跨境电商数据分析系统

这是一个经过脱敏整理的前后端 monorepo，用于展示跨境电商数据采集、清洗、分析和可视化能力。仓库不包含真实店铺数据、平台凭据、数据库备份、运行日志或导出文件。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia、ECharts、Axios
- 后端：FastAPI、SQLAlchemy 2.0 Async、MySQL、Alembic、APScheduler
- 平台集成：Wildberries Seller API、Ozon Seller/Performance API
- 部署：Docker、Docker Compose、Nginx

## 目录

```text
.
├── client/               # Vue 前端
├── server/               # FastAPI 后端
├── docker-compose.yml    # 本地演示环境
├── .env.example          # Docker Compose 占位配置
└── SECURITY.md           # 凭据与数据安全说明
```

## 本地启动

1. 生成本地配置：

   ```bash
   cp .env.example .env
   ```

2. 将 `.env` 中所有 `REPLACE_ME` 值替换为仅用于本机的随机值。不要提交 `.env`。

3. 构建并启动：

   ```bash
   docker compose up --build
   ```

4. 创建演示登录账号（密码不会写入代码或日志）：

   ```bash
   docker compose exec \
     -e DEMO_EMAIL=demo@example.com \
     -e DEMO_PASSWORD='your-local-demo-password' \
     backend python scripts/init_demo_user.py
   ```

5. 打开：

   - 前端：<http://localhost:5173>
   - API 文档：<http://localhost:8000/docs>

新数据库默认没有业务数据。可登录后自行创建测试店铺，或者在本地编写不含真实信息的模拟数据。定时同步任务在演示配置中默认关闭。

## 安全边界

- 不提供任何真实 API Key、数据库密码、JWT 密钥或平台账号。
- 不包含 SQL 备份、日志、接口响应样本、Excel/CSV 导出或上传文件。
- Docker 演示环境设置 `JOBS_ENABLED=false`、`RUN_SCHEDULER=false`，不会自动访问外部平台。
- 若需要接入真实平台，请只在本地 `.env` 或数据库中配置凭据，并确保仓库保持 private。

## 发布建议

在 GitHub 创建 **Private repository**，然后从本目录初始化全新的 Git 历史。不要把原始 Gitee 仓库的旧历史合并进来，因为旧历史可能包含已经删除的日志或配置文件。
