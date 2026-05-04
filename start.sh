#!/usr/bin/env bash
# ============================================================
# Linux / macOS 启动脚本
# 用途：激活虚拟环境，从 .env 读取 HOST/PORT 后启动 FastAPI
# 用法：
#   ./start.sh               前台运行（读取 .env 中的 HOST/PORT）
#   ./start.sh 8080          前台运行，端口以命令行参数覆盖
#   ./start.sh --background  后台运行（日志写入 run.log，PID 写入 run.pid）
#   ./start.sh stop          停止后台运行的进程
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 从 .env 读取默认值 ───────────────────────────────────────
HOST="0.0.0.0"
PORT="8000"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key value; do
        # 跳过注释与空行
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        key="${key// /}"
        value="${value%%#*}"  # 去掉行内注释
        value="${value// /}"
        case "$key" in
            HOST) HOST="$value" ;;
            PORT) PORT="$value" ;;
        esac
    done < "$ENV_FILE"
else
    echo "[WARN] 未找到 .env 文件，使用默认值 HOST=$HOST PORT=$PORT"
fi

# ── 参数解析（命令行可覆盖端口）─────────────────────────────
BACKGROUND=false
STOP=false

for arg in "$@"; do
    case "$arg" in
        --background|-b) BACKGROUND=true ;;
        stop)            STOP=true ;;
        [0-9]*)          PORT="$arg" ;;
    esac
done

# ── 停止后台进程 ────────────────────────────────────────────
if [ "$STOP" = true ]; then
    if [ ! -f run.pid ]; then
        echo "[WARN] 未找到 run.pid，进程可能未在运行。"
        exit 0
    fi
    PID=$(cat run.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "[INFO] 已发送终止信号，PID=$PID"
        rm -f run.pid
    else
        echo "[WARN] PID=$PID 对应进程不存在，清理 run.pid"
        rm -f run.pid
    fi
    exit 0
fi

# ── 检查虚拟环境 ────────────────────────────────────────────
VENV_ACTIVATE="$SCRIPT_DIR/.venv/bin/activate"

if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "[ERROR] 未找到虚拟环境，请先执行：python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# shellcheck source=/dev/null
source "$VENV_ACTIVATE"

# ── 启动服务 ────────────────────────────────────────────────
cd "$SCRIPT_DIR"

if [ "$BACKGROUND" = true ]; then
    echo "[INFO] 后台启动 FastAPI 服务，监听 $HOST:$PORT，日志 → run.log"
    nohup python -m uvicorn app.main:app --host "$HOST" --port "$PORT" > run.log 2>&1 &
    echo $! > run.pid
    echo "[INFO] PID=$(cat run.pid)，使用 './start.sh stop' 可停止服务"
else
    echo "[INFO] 前台启动 FastAPI 服务，监听 $HOST:$PORT ..."
    python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi
