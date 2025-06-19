# Vertex CLI 完整使用指南

Vertex是一个本地AI工作流系统，提供多种运行模式和丰富的命令行功能。

## 🚀 快速开始

```bash
# 安装vertex
pip install -e .

# 查看帮助
vertex --help

# 启动标准模式（默认）
vertex

# 查看版本
vertex --version
```

## 📋 命令概览

Vertex CLI提供以下主要命令：

| 命令 | 功能 | 说明 |
|------|------|------|
| `vertex` | 标准模式 | 启动Vertex聊天界面（默认） |
| `vertex run` | 标准模式 | 同上，显式指定 |
| `vertex workflow` | 工作流模式 | 启动VertexFlow可视化编辑器 |
| `vertex config` | 配置管理 | 管理系统配置文件 |
| `vertex rag` | RAG问答 | 基于文档的智能问答系统 |

## 🎯 详细使用说明

### 1. 标准模式 (Standard Mode)

启动Vertex标准聊天界面，提供基础的AI对话功能。

```bash
# 使用默认配置启动
vertex
# 或
vertex run

# 指定Web服务端口
vertex run --port 8080

# 指定主机地址
vertex run --host 0.0.0.0 --port 8080
```

**功能特性**：
- ✅ 多模型支持（OpenRouter、DeepSeek等）
- ✅ Web界面聊天
- ✅ 对话历史管理
- ✅ 响应式设计

### 2. 工作流模式 (Workflow Mode)

启动VertexFlow可视化工作流编辑器，支持拖拽式工作流设计。

```bash
# 启动工作流编辑器
vertex workflow

# 指定端口
vertex workflow --port 8999
```

**功能特性**：
- ✅ 可视化工作流设计
- ✅ 拖拽式节点编辑
- ✅ 实时工作流执行
- ✅ 工作流模板管理

### 3. 配置管理 (Config Management)

管理Vertex系统的配置文件，支持多种配置操作。

#### 3.1 配置初始化

```bash
# 快速初始化配置（使用默认模板）
vertex config init

# 交互式配置向导
vertex config setup
```

#### 3.2 配置检查

```bash
# 检查配置状态
vertex config check
```

输出示例：
```
配置检查结果:
  模板存在: ✓
  配置存在: ✓
  配置有效: ✓
  模板路径: /path/to/vertex_flow/config/llm.yml.template
  配置路径: /path/to/vertex_flow/config/llm.yml

建议运行: vertex config init
```

#### 3.3 配置重置

```bash
# 重置配置为默认模板
vertex config reset
```

**配置文件结构**：
```yaml
llm:
  openrouter:
    sk: your-api-key
    enabled: true
    model-name: deepseek/deepseek-chat-v3-0324:free

embedding:
  local:
    enabled: true
    model_name: "all-MiniLM-L6-v2"
    use_mirror: true

vector:
  local:
    enabled: true
    dimension: 384
```

### 4. RAG问答系统 (RAG Mode)

基于文档的检索增强生成系统，提供智能文档问答功能。

#### 4.1 基础用法

```bash
# 使用内置示例文档
vertex rag

# 索引指定目录的文档
vertex rag -d ./documents

# 显示向量数据库统计
vertex rag --show-stats
```

#### 4.2 查询模式

```bash
# 直接查询（完整模式）
vertex rag --query "什么是人工智能？"

# 快速查询（跳过LLM生成）
vertex rag --query "什么是人工智能？" --fast

# 交互式问答
vertex rag --interactive

# 快速交互式查询
vertex rag --interactive --fast
```

#### 4.3 文档管理

```bash
# 强制重新索引文档
vertex rag -d ./documents --reindex

# 组合使用：重新索引后查询
vertex rag -d ./documents --reindex --query "文档摘要"
```

#### 4.4 性能模式对比

| 模式 | 命令 | 耗时 | 功能 |
|------|------|------|------|
| 完整查询 | `--query "问题"` | 3-8秒 | 文档检索 + LLM生成 |
| 快速查询 | `--query "问题" --fast` | 0.5-1秒 | 仅文档检索 |
| 仅索引 | `-d path --reindex` | 按文档量 | 仅构建索引 |
| 统计信息 | `--show-stats` | <1秒 | 显示数据库状态 |

## 🛠️ 高级用法

### 环境变量配置

支持通过环境变量覆盖配置：

```bash
# 指定配置文件
export CONFIG_FILE=config/llm.yml.backup

# 指定LLM API密钥
export llm_openrouter_sk=your-api-key

# 指定服务端口
export VERTEX_PORT=8080

# 运行系统
vertex
```

### 脚本集成

Vertex CLI可以集成到自动化脚本中：

```bash
#!/bin/bash

# 自动化文档处理脚本
echo "开始处理文档..."

# 索引新文档
vertex rag -d ./new_documents --reindex

# 批量查询并保存结果
questions=("文档主要内容" "关键技术点" "应用场景")

for question in "${questions[@]}"; do
    echo "查询: $question"
    vertex rag --query "$question" --fast > "result_${question// /_}.txt"
done

echo "处理完成！"
```

### Docker部署

```dockerfile
FROM python:3.9-slim

COPY . /app
WORKDIR /app

RUN pip install -e .

# 暴露端口
EXPOSE 8080

# 默认启动命令
CMD ["vertex", "run", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# 构建镜像
docker build -t vertex-ai .

# 运行容器
docker run -p 8080:8080 -v ./config:/app/config vertex-ai

# 运行工作流模式
docker run -p 8999:8999 vertex-ai vertex workflow --port 8999
```

## 🔧 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   # 错误：ImportError: No module named 'vertex_flow'
   # 解决：确保正确安装
   pip install -e .
   ```

2. **配置文件问题**
   ```bash
   # 错误：配置文件不存在
   # 解决：初始化配置
   vertex config init
   ```

3. **端口占用**
   ```bash
   # 错误：Address already in use
   # 解决：指定其他端口
   vertex run --port 8081
   ```

4. **RAG依赖缺失**
   ```bash
   # 错误：ImportError: No module named 'sentence_transformers'
   # 解决：安装RAG依赖
   pip install sentence-transformers faiss-cpu
   ```

### 调试模式

```bash
# 设置调试模式
export VERTEX_DEBUG=1

# 查看详细日志
vertex run 2>&1 | tee vertex.log

# RAG调试
export CONFIG_FILE=config/llm.yml.backup
vertex rag --query "test" --fast
```

### 性能优化

```bash
# 1. 使用国内镜像源（首次运行较慢）
export HF_ENDPOINT=https://hf-mirror.com

# 2. 预热模型缓存
vertex rag --show-stats

# 3. 使用快速模式进行批量查询
vertex rag --interactive --fast
```

## 📚 实用示例

### 场景1：开发环境搭建

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/localqwen.git
cd localqwen

# 2. 安装依赖
pip install -e .
pip install sentence-transformers faiss-cpu

# 3. 初始化配置
vertex config init

# 4. 测试运行
vertex rag --show-stats
```

### 场景2：文档知识库构建

```bash
# 1. 索引项目文档
vertex rag -d ./docs --reindex

# 2. 测试查询
vertex rag --query "如何使用RAG功能？"

# 3. 启动交互式查询
vertex rag --interactive
```

### 场景3：批量文档处理

```bash
# 1. 处理多个目录
for dir in docs1 docs2 docs3; do
    vertex rag -d ./$dir --reindex
done

# 2. 批量查询
queries=(
    "技术概述"
    "安装步骤"
    "使用示例"
)

for query in "${queries[@]}"; do
    echo "=== $query ==="
    vertex rag --query "$query" --fast
    echo ""
done
```

### 场景4：CI/CD集成

```yaml
# .github/workflows/docs-qa.yml
name: 文档问答测试

on: [push, pull_request]

jobs:
  test-rag:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install sentence-transformers faiss-cpu
    
    - name: Initialize config
      run: vertex config init
    
    - name: Index documentation
      run: vertex rag -d ./docs --reindex
    
    - name: Test queries
      run: |
        vertex rag --query "安装说明" --fast
        vertex rag --query "使用方法" --fast
```

## 🔗 相关文档

- [RAG CLI详细说明](./RAG_CLI_USAGE.md)
- [RAG性能优化](./RAG_PERFORMANCE_OPTIMIZATION.md)
- [配置文件说明](./CONFIG_REFERENCE.md)
- [工作流设计指南](./WORKFLOW_GUIDE.md)

## 🆘 获取帮助

```bash
# 查看命令帮助
vertex --help
vertex config --help
vertex rag --help

# 查看版本信息
vertex --version

# 在线文档
# https://github.com/your-repo/localqwen/tree/main/docs
```

---

通过这个完整的CLI指南，你可以充分利用Vertex的所有功能，从基础聊天到高级工作流设计，再到智能文档问答系统。选择适合你需求的模式，享受AI驱动的工作流体验！ 