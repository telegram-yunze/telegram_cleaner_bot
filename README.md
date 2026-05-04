# Telegram Cleaner Bot

基于 FastAPI + aiogram 构建的 Telegram 群组自动审核机器人，支持风控规则管理、违规消息处置、处置记录查询与 Webhook/Polling 双模式运行。

---

## 功能概览

- **规则引擎**：支持关键词、正则、链接、用户名、联系方式、AI 检测六种规则类型
- **自动处置**：命中规则后可执行删除、警告、禁言、限制权限、踢出、封禁等动作
- **惩罚升级策略**：可配置自动升级（warn → mute → kick → ban），累计次数超阈值自动升级
- **广告检测**：内置启发式广告打分引擎，支持链接、@提及、关键词等特征融合评分
- **处置记录**：所有审核动作均记录可查，支持按群组、成员、状态等多维度检索
- **群组管理**：自动同步群组信息、成员资料与机器人权限快照
- **通知与撤回**：可配置处置后发送提示消息，并在指定延迟后自动撤回
- **双模式支持**：同时支持 Webhook 与 Polling 运行，可按需切换
- **REST API**：提供完整的 RESTful 管理接口，支持 API Key 鉴权，内置 Swagger 文档

---

## 技术栈

| 分类 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.136 + uvicorn |
| Telegram SDK | aiogram 3.27 |
| ORM | SQLAlchemy 2.0（异步） |
| 数据库迁移 | Alembic |
| 数据库 | SQLite（开发）/ PostgreSQL 或 MySQL（生产） |
| 数据校验 | Pydantic v2 |
| 缓存 | cashews（内存或 Redis） |
| 配置管理 | pydantic-settings + .env |
| 代理支持 | aiohttp-socks（HTTP/SOCKS5） |

---

## 目录结构

```
telegram_cleaner_bot/
├── app/
│   ├── api/           # FastAPI 路由层（groups、rules、moderation、webhook、health）
│   ├── bot/           # aiogram 机器人逻辑（dispatcher、handlers、filters）
│   ├── db/            # 数据库 Session 与 Base 定义
│   ├── middleware/    # 请求中间件（RequestContext、request_id 注入）
│   ├── models/        # SQLAlchemy ORM 模型与 JSON 列结构体
│   ├── repositories/  # 数据访问层（JPA 风格命名，接口 + 实现）
│   ├── schemas/       # Pydantic 请求/响应 Schema
│   ├── services/      # 业务逻辑层（规则匹配、处置执行、广告检测等）
│   ├── tasks/         # 后台定时任务（群组信息同步）
│   ├── utils/         # 工具函数（日志、安全）
│   ├── config.py      # 全局配置（pydantic-settings）
│   └── main.py        # FastAPI 应用入口
├── migrations/        # Alembic 迁移脚本
├── tests/             # 单元测试与集成测试
├── resources/         # 静态资源（Bot 文案等）
├── .env.example       # 配置模板
├── start.sh           # Linux/macOS 启动脚本
├── start.bat          # Windows 启动脚本
└── requirements.txt   # Python 依赖
```

---

## 快速开始

### 1. 克隆项目并创建虚拟环境

```bash
git clone <仓库地址>
cd telegram_cleaner_bot

# 创建虚拟环境
python -m venv .venv

# 激活（Linux/macOS）
source .venv/bin/activate

# 激活（Windows）
.venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制配置模板并填写实际值：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写以下必填项：

```dotenv
# 从 @BotFather 获取
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# API 鉴权密钥（建议用 openssl rand -hex 32 生成）
API_SECRET_KEY=change-me-to-a-random-32-char-string

# Webhook 模式时需填写（Polling 模式可留空）
WEBHOOK_BASE_URL=https://your-domain.com
```

### 4. 初始化数据库

```bash
alembic upgrade head
```

### 5. 启动服务

**Linux/macOS：**

```bash
# 前台运行
./start.sh

# 后台运行（日志写入 run.log）
./start.sh --background

# 停止后台进程
./start.sh stop
```

**Windows：**

```bat
start.bat
```

**或使用 uvicorn 直接启动（开发模式）：**

```bash
uvicorn app.main:app --reload
```

服务启动后默认监听 `http://0.0.0.0:8000`。

---

## 配置说明

所有配置均通过 `.env` 文件或环境变量注入，下表列出常用配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./telegram_cleaner_bot.db` | 数据库连接串 |
| `SQLALCHEMY_ECHO` | `false` | 是否打印 SQL 语句到日志 |
| `DEBUG` | `false` | 调试模式，生产必须关闭 |
| `HOST` | `0.0.0.0` | uvicorn 监听地址 |
| `PORT` | `8000` | uvicorn 监听端口 |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `API_PREFIX` | `/api` | API 路由前缀 |
| `TELEGRAM_BOT_TOKEN` | —（必填） | Telegram Bot Token |
| `TELEGRAM_RUN_MODE` | `both` | 运行模式：`webhook` / `polling` / `both` / `disabled` |
| `TELEGRAM_ACTION_DRY_RUN` | `true` | 是否为空跑模式（不真实执行处置动作） |
| `TELEGRAM_PROXY_URL` | `""` | 代理地址，如 `http://127.0.0.1:7890` 或 `socks5://127.0.0.1:1080` |
| `WEBHOOK_BASE_URL` | `""` | Webhook 公网 HTTPS 地址 |
| `WEBHOOK_PATH` | `/webhook/telegram` | Webhook 路径 |
| `WEBHOOK_SECRET_TOKEN` | `""` | Telegram Webhook 安全令牌 |
| `API_SECRET_KEY` | —（必填） | REST API 鉴权密钥 |
| `CACHE_URL` | `mem://` | 缓存连接串，生产可改为 `redis://host:6379` |

> **注意**：`TELEGRAM_ACTION_DRY_RUN=true` 时机器人不会真实执行禁言/踢出等操作，仅记录处置结果，适合测试环境。

---

## API 文档

服务启动后可访问以下地址查看交互式 API 文档：

- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`

### 鉴权方式

所有业务接口（健康检查与 Webhook 除外）需在请求头中携带 API Key：

```
X-API-Key: <API_SECRET_KEY>
```

### 接口概览

| 分类 | 前缀 | 说明 |
|------|------|------|
| 健康检查 | `GET /api/health` | 服务探活与联通性校验 |
| 群组管理 | `/api/groups` | 群组信息增删改查 |
| 规则管理 | `/api/rules` | 风控规则增删改查 |
| 处置记录 | `/api/moderation` | 审核处置记录查询与状态更新 |
| Webhook | `POST /webhook/telegram` | Telegram 更新事件回调 |

---

## 运行模式说明

通过 `TELEGRAM_RUN_MODE` 控制机器人接收更新的方式：

| 模式 | 说明 |
|------|------|
| `polling` | 长轮询模式，适合本地开发，无需公网域名 |
| `webhook` | Webhook 模式，适合生产部署，需要 HTTPS 公网地址 |
| `both` | 同时启用两种模式（默认，启动时自动注册 Webhook，Polling 作为备用） |
| `disabled` | 禁用机器人，仅运行 REST API 服务 |

---

## 数据库迁移

```bash
# 创建新迁移（修改 ORM 模型后执行）
alembic revision --autogenerate -m "描述变更内容"

# 执行迁移，升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看当前版本
alembic current
```

> **重要**：数据库迁移必须由人工手动执行，服务启动时不会自动迁移。

---

## 运行测试

```bash
python -m unittest tests.test_api_auth tests.test_api_exception_handling tests.test_request_id_integration -v
```

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

---

## Linux 后台部署

```bash
# 后台运行（日志写入 run.log，PID 写入 run.pid）
./start.sh --background

# 查看实时日志
tail -f run.log

# 查看进程是否在运行
pid=$(cat run.pid)
ps -p $pid

# 停止服务
./start.sh stop
# 或强制停止
kill -9 $(cat run.pid)

# 更新代码后重启
git stash
git pull
git stash pop
./start.sh stop
./start.sh --background
```

---

## 生产部署建议

1. **数据库**：替换 SQLite 为 PostgreSQL（`postgresql+asyncpg://...`）或 MySQL（`mysql+aiomysql://...`）
2. **缓存**：将 `CACHE_URL` 改为 Redis 地址（`redis://host:6379`）
3. **安全**：`DEBUG=false`，`TELEGRAM_ACTION_DRY_RUN=false`，`API_SECRET_KEY` 使用高强度随机字符串
4. **代理**：国内服务器访问 Telegram API 需配置 `TELEGRAM_PROXY_URL`
5. **反向代理**：建议使用 Nginx 做 HTTPS 终止，将请求代理到 `localhost:8000`
6. **进程守护**：可用 systemd 或 supervisor 管理进程，避免宕机后无法自动重启

---

## 许可证

本项目为私有项目，请勿公开分发。
