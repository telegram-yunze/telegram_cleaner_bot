@echo off
chcp 65001 > nul
:: ============================================================
:: Windows 启动脚本
:: 用途：激活虚拟环境，从 .env 读取 HOST/PORT 后启动 FastAPI
:: 用法：
::   start.bat            前台运行（读取 .env 中的 HOST/PORT）
::   start.bat 8080       前台运行，端口以命令行参数覆盖
:: ============================================================

setlocal EnableDelayedExpansion

:: ── 默认值 ──────────────────────────────────────────────────
set HOST=0.0.0.0
set PORT=8000

:: ── 读取 .env 文件（跳过注释与空行）────────────────────────
set ENV_FILE=%~dp0.env
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        set LINE=%%A
        if not "!LINE:~0,1!"=="#" (
            if /i "%%A"=="HOST" set HOST=%%B
            if /i "%%A"=="PORT" set PORT=%%B
        )
    )
) else (
    echo [WARN] 未找到 .env 文件，使用默认值 HOST=%HOST% PORT=%PORT%
)

:: ── 命令行参数可覆盖端口 ─────────────────────────────────────
if not "%~1"=="" set PORT=%~1

:: ── 检查虚拟环境 ─────────────────────────────────────────────
set VENV_ACTIVATE=%~dp0.venv\Scripts\activate.bat
if not exist "%VENV_ACTIVATE%" (
    echo [ERROR] 未找到虚拟环境，请先执行：python -m venv .venv
    pause
    exit /b 1
)

call "%VENV_ACTIVATE%"

echo [INFO] 启动 FastAPI 服务，监听 %HOST%:%PORT% ...
python -m uvicorn app.main:app --host %HOST% --port %PORT% --reload

endlocal
