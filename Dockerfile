# ============================================================
# 多阶段构建：先安装依赖，再复制应用代码，减小最终镜像体积
# ============================================================

# ── 阶段一：安装 Python 依赖 ──────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装构建工具（aiohttp、pydantic-core 等需要编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 优先复制依赖文件，利用 Docker 层缓存
# 只要 requirements.txt 不变，此层不会重新执行
COPY requirements.txt .

# 将依赖安装到独立目录，方便后续阶段复制
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── 阶段二：最终运行镜像 ───────────────────────────────────────
FROM python:3.12-slim AS runtime

# 设置时区
ENV TZ=Asia/Shanghai

# 禁止 Python 生成 .pyc 文件，减少磁盘写入
ENV PYTHONDONTWRITEBYTECODE=1
# 禁止输出缓冲，保证日志实时输出到 stdout
ENV PYTHONUNBUFFERED=1
# 将项目根目录加入 Python 模块搜索路径
ENV PYTHONPATH=/app

# 创建非 root 用户，避免以 root 身份运行服务（安全最佳实践）
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

# 将 builder 阶段安装好的依赖复制到系统路径
COPY --from=builder /install /usr/local

WORKDIR /app

# 复制应用代码（.dockerignore 已排除 .env、.venv、__pycache__、*.db 等）
COPY --chown=appuser:appgroup . .

# 切换为非 root 用户
USER appuser

EXPOSE 8000

# 健康检查：每 30 秒探测一次，启动后等待 15 秒再开始
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 生产环境建议根据 CPU 核数调整 --workers
CMD ["python", "-m", "uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "1", \
    "--log-level", "info"]
