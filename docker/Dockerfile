# 使用官方Python镜像作为基础镜像
FROM python:3.12-slim

# 创建admin用户
RUN groupadd -r admin && useradd -r -g admin admin

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8999
ENV HOST=0.0.0.0

# 安装基础系统依赖
RUN apt-get update && apt-get install -y \
        curl \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
RUN pip install uv

# 复制项目文件（使用root用户复制）
COPY pyproject.toml .
COPY requirements.txt .
COPY vertex_flow/ ./vertex_flow/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY README*.md ./
COPY LICENSE ./

# 使用root用户安装Python依赖
RUN uv pip install --system -e .

# 复制配置文件模板
COPY vertex_flow/config/llm.yml.template ./config/llm.yml

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/reports /app/.vertex/config && \
    chown -R admin:admin /app

# 切换到admin用户
USER admin

# 暴露端口
EXPOSE 8999

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8999/health || exit 1

# 设置默认命令 - 启动工作流web服务
CMD ["python", "-m", "vertex_flow.cli", "workflow", "--host", "0.0.0.0", "--port", "8999"] 