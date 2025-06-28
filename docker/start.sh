#!/bin/bash

# 启动脚本 - 用于调试容器启动问题

echo "Starting Vertex Flow application..."

# 检查Python环境
echo "Python version:"
python --version

echo "Python path:"
python -c "import sys; print(sys.path)"

# 检查vertex_flow模块
echo "Checking vertex_flow module..."
python -c "import vertex_flow; print('vertex_flow imported successfully')"

# 检查配置文件
echo "Checking config file..."
if [ -f "/app/config/llm.yml" ]; then
    echo "Config file exists: /app/config/llm.yml"
else
    echo "Config file not found: /app/config/llm.yml"
fi

# 启动应用
echo "Starting application with host: $HOST, port: $PORT"
exec python -m vertex_flow.cli workflow --host "$HOST" --port "$PORT" 