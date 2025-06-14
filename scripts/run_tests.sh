#!/bin/bash

# 运行单元测试脚本
# 设置脚本在遇到错误时退出
set -e

echo "开始运行单元测试..."

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查是否存在虚拟环境
if [ -d ".venv" ]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
fi

# 检测并使用合适的包管理工具
echo "检测包管理工具..."

# 检查是否有uv命令可用
if command -v uv >/dev/null 2>&1; then
    echo "使用uv进行依赖管理..."
    PYTHON_CMD="uv run python"
    PIP_CMD="uv pip"
    
    # 使用uv安装依赖
    uv pip install -r requirements.txt
    uv pip install -e .
    uv pip install pytest pytest-cov pytest-asyncio
    
else
    echo "使用标准python/pip进行依赖管理..."
    
    # 检查是否在虚拟环境中或有python命令
    if command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
        PIP_CMD="python -m pip"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
        PIP_CMD="python3 -m pip"
    else
        echo "❌ 未找到python命令！"
        exit 1
    fi
    
    # 安装依赖
    echo "安装测试依赖..."
    $PIP_CMD install -r requirements.txt
    $PIP_CMD install -e .
    $PIP_CMD install pytest pytest-cov pytest-asyncio
fi

# 运行测试
echo "运行pytest测试..."
if command -v uv >/dev/null 2>&1; then
    uv run pytest vertex_flow/tests/ -v --tb=short --cov=vertex_flow --cov-report=term-missing
else
    $PYTHON_CMD -m pytest vertex_flow/tests/ -v --tb=short --cov=vertex_flow --cov-report=term-missing
fi

# 检查测试结果
if [ $? -eq 0 ]; then
    echo "✅ 所有测试通过！"
else
    echo "❌ 测试失败！"
    exit 1
fi