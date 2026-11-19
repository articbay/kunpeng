# 跨境电商数据采集系统 - 后端

## 技术栈

- **Web框架**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: MySQL + asyncmy
- **认证**: JWT
- **任务调度**: APScheduler
- **配置管理**: Pydantic Settings

## 快速开始

### 1. 安装依赖

```bash
poetry install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等
```

### 3. 初始化数据库和创建本地演示用户

不要在源码中保存默认密码。先通过环境变量提供仅用于本机的账号信息：

```bash
DEMO_EMAIL=demo@example.com \
DEMO_PASSWORD='your-local-demo-password' \
poetry run python scripts/init_demo_user.py
```

脚本只创建演示用户，不创建店铺，不写入任何平台 API Key。

### 4. 启动开发服务器

```bash
poetry run uvicorn kunpeng.main:app --reload
实际后端启动：.\.venv\Scripts\python.exe -m uvicorn kunpeng.main:app --reload
```
poetry run uvicorn kunpeng.main:app --app-dir ./src --reload
### 4. 启动任务调度器

```bash
poetry run python scripts/run_scheduler.py
```
```
poetry run python -m kunpeng.scheduler_main //新代码
```

## API文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
src/kunpeng/
├── api/              # API路由层
│   ├── deps.py       # 依赖注入
│   └── v1/          # API v1版本
├── config/           # 配置模块
├── core/             # 基础设施
│   ├── database.py   # 数据库连接
│   ├── security.py   # JWT认证
│   └── scheduler.py  # 任务调度器
├── models/           # SQLAlchemy模型
├── schemas/          # Pydantic schemas
├── crud/             # CRUD层
├── clients/          # 平台API客户端
├── services/         # 业务逻辑
├── jobs/             # 定时任务
└── utils/            # 工具类
```

## 开发指南

### 添加新的API端点

1. 在 `schemas/` 中定义Pydantic模型
2. 在 `models/` 中定义SQLAlchemy模型
3. 在 `crud/` 中实现CRUD操作
4. 在 `api/v1/` 中添加路由

### 添加新的定时任务

1. 在 `jobs/` 中创建任务函数
2. 在 `core/scheduler.py` 中注册任务

## 许可证

MIT
