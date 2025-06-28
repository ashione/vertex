# 使用官方Python镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装基础系统依赖
RUN apt-get update && apt-get install -y \
        curl \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
RUN pip install uv

# 只复制whl包和必要文件
COPY dist/vertex-0.1.0-py3-none-any.whl .
COPY requirements.txt .
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY README*.md ./
COPY LICENSE ./

# 安装whl包
RUN uv pip install --system vertex-0.1.0-py3-none-any.whl

# 复制配置文件模板
COPY vertex_flow/config/llm.yml.template ./config/llm.yml
RUN mkdir -p /usr/local/lib/python3.12/site-packages/config && cp ./config/llm.yml /usr/local/lib/python3.12/site-packages/config/llm.yml

# 暴露端口（如果需要Web UI）
EXPOSE 7860
EXPOSE 8999

# 设置默认命令
CMD ["python", "-m", "vertex_flow.cli", "workflow"] 