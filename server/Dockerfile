# Dockerfile for Kunpeng Backend
# 优化版本 - 使用国内镜像源，解决构建慢的问题
FROM python:3.11-slim-bookworm AS builder

# Set working directory
WORKDIR /app

# ===== 优化 1: 配置 Debian 国内镜像源 =====
# 备份原配置
RUN cp -a /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources.backup

# 方法 1: 使用 sed 替换（兼容新旧格式）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        # 尝试替换 Debian 12 sources 格式
        sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources; \
        sed -i 's|security.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    # 兼容旧格式（如果存在）
    if [ -f /etc/apt/sources.list ]; then \
        cp -a /etc/apt/sources.list /etc/apt/sources.list.backup; \
        sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list; \
        sed -i 's/security.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list; \
    fi

# ===== 优化 2: 安装依赖时配置超时和重试 =====
# Install system dependencies for building
RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libmariadb-dev \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ===== 优化 3: 使用国内 PyPI 镜像安装 Poetry =====
RUN pip install --no-cache-dir --index-url https://mirrors.cloud.tencent.com/pypi/simple poetry==1.7.0

# Copy dependency files and source
COPY pyproject.toml poetry.lock ./
COPY src ./src

# Configure poetry and install dependencies
# 关键修复: poetry.lock 中固定了 pypi.org 的下载地址，国内直连极慢/卡死。
# 改为用 poetry 导出依赖清单，再用 pip + 腾讯云镜像安装（pip 的 --index-url 会真正走镜像）。
ENV PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple \
    PIP_DEFAULT_TIMEOUT=120
RUN poetry config virtualenvs.create false \
    && poetry export -f requirements.txt --without-hashes --without dev -o /tmp/requirements.txt \
    && pip install --no-cache-dir --index-url https://mirrors.cloud.tencent.com/pypi/simple --retries 5 --timeout 120 -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim-bookworm AS production

# Set working directory
WORKDIR /app

# ===== 优化 1: 配置 Debian 国内镜像源 =====
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources; \
        sed -i 's|security.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list; \
        sed -i 's/security.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list; \
    fi

# Install system dependencies (含 tzdata：zoneinfo 解析 Europe/Moscow 需要时区数据库)
RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libmariadb-dev \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple \
    TZ=Europe/Moscow

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "kunpeng.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
