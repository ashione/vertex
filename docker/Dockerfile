# 使用官方Python镜像作为基础镜像 - 明确指定架构避免exec format error
FROM --platform=linux/amd64 python:3.12-slim

# 创建admin用户
RUN groupadd -r admin && useradd -r -g admin admin

# 设置工作目录
WORKDIR /app

# 设置环境变量 - 适配SAE标准端口
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
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

# 复制启动脚本
COPY docker/start.sh ./start.sh

# 创建必要的目录
RUN mkdir -p /app/logs /app/reports /app/.vertex/config

# 设置所有文件的所有权和权限（在切换到admin用户之前）
RUN chown -R admin:admin /app && \
    chmod +x /app/start.sh && \
    chmod +x /app/scripts/*.sh 2>/dev/null || true

# 切换到admin用户
USER admin

# 暴露端口 - SAE标准端口
EXPOSE 8080

# 健康检查 - 适配SAE要求
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 设置默认命令 - 使用start.sh脚本
CMD ["./start.sh"] 