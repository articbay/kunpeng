@echo off
chcp 65001 >nul
echo ========================================
echo 鲲鹏后端 API 启动脚本
echo ========================================
echo.

REM 设置 PYTHONPATH
set PYTHONPATH=%~dp0src;%PYTHONPATH%

REM 切换到项目目录
cd /d "%~dp0"

echo 正在启动后端 API...
echo 访问地址:
echo   - 健康检查: http://127.0.0.1:8000/health
echo   - API文档: http://127.0.0.1:8000/docs
echo.

REM 直接使用 uvicorn
python -m uvicorn kunpeng.main:app --reload

if errorlevel 1 (
    echo.
    echo 启动失败！请检查:
    echo   1. 是否在正确的虚拟环境中
    echo   2. 依赖是否已安装
    echo   3. 端口 8000 是否被占用
    echo.
    pause
)
