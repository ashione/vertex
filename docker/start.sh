#!/bin/bash

# SAE生产环境启动脚本

set -e

echo "=== SAE Vertex Flow Startup ==="
echo "Environment: HOST=$HOST, PORT=$PORT"

# 设置默认环境变量
export PORT=${PORT:-8080}
export HOST=${HOST:-0.0.0.0}

# 快速检查Python环境
python --version > /dev/null 2>&1 || { echo "Error: Python not found"; exit 1; }

# 检查vertex_flow模块
python -c "import vertex_flow; print('✓ Module loaded successfully')" || { echo "Error: Failed to import vertex_flow"; exit 1; }

# 检查配置文件
if [ ! -f "/app/config/llm.yml" ]; then
    echo "Warning: Config file not found at /app/config/llm.yml"
fi

# 启动应用
echo "Starting application on $HOST:$PORT"
exec python -m vertex_flow.cli workflow --host "$HOST" --port "$PORT" 