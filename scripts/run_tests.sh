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

# 安装依赖（如果需要）
echo "安装测试依赖..."
pip install -r requirements.txt
pip install pytest pytest-cov

# 运行测试
echo "运行pytest测试..."
pytest vertex_flow/tests/ -v --tb=short --cov=vertex_flow --cov-report=term-missing

# 检查测试结果
if [ $? -eq 0 ]; then
    echo "✅ 所有测试通过！"
else
    echo "❌ 测试失败！"
    exit 1
fi