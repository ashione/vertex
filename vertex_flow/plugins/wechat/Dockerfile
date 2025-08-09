# 微信公众号插件独立部署 Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制插件代码
COPY . /app/

# 创建日志目录
RUN mkdir -p /app/logs

# 创建非root用户
RUN useradd -m -u 1000 wechat && chown -R wechat:wechat /app
USER wechat

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# 启动命令
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8001"]