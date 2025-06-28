#!/bin/bash

# 简化的测试启动脚本

echo "=== Vertex Flow Container Test ==="
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Environment variables:"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  HOST: $HOST"
echo "  PORT: $PORT"

echo ""
echo "=== Python Environment ==="
python --version
python -c "import sys; print('Python executable:', sys.executable)"

echo ""
echo "=== Module Test ==="
python -c "
try:
    import vertex_flow
    print('✓ vertex_flow imported successfully')
except ImportError as e:
    print('✗ vertex_flow import failed:', e)
"

echo ""
echo "=== Config Test ==="
if [ -f "/app/config/llm.yml" ]; then
    echo "✓ Config file exists"
    ls -la /app/config/
else
    echo "✗ Config file not found"
    echo "Available files in /app:"
    ls -la /app/
fi

echo ""
echo "=== Starting Application ==="
# 尝试启动应用
python -m vertex_flow.cli workflow --host "$HOST" --port "$PORT" 