


          
# Vertex - LLM/GraphLLM 工具

Vertex 是一个支持本地和云端大语言模型（LLM）推理的工具，提供简洁易用的 Web 聊天界面。支持本地 Ollama 部署的 Qwen-7B 模型，也可通过 API 调用外部模型。

## 功能特性

- 支持本地 Ollama 部署的 Qwen-7B 模型（chatbox 聊天界面）
- 支持通过 API 方式调用 DeepSeek 等外部模型
- Web UI 聊天体验，支持上下文多轮对话
- 可扩展的客户端架构，便于集成更多模型
- 支持流式输出，实时显示生成内容

## 环境要求

- Python 3.8 及以上
- Ollama（本地模型推理，详见 https://ollama.com ）

## 安装步骤

1. 安装 Ollama

   - 访问 [https://ollama.com/download](https://ollama.com/download)
   - 下载并安装适用于您系统的 Ollama

2. 克隆本仓库

   ```bash
   git clone git@github.com:ashione/vertex.git
   cd vertex
   ```

3. 安装依赖

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## 快速启动

### 方式一：命令行启动（推荐）

```bash
vertex
```

### 方式二：直接运行主程序

```bash
python src/app.py
```

### 方式三：开发模式运行

```bash
python -m src.app
```

启动后，浏览器访问 [http://localhost:7860](http://localhost:7860) 进入 Web 聊天界面。

## 可选参数

- `--host`：Ollama 服务地址（默认：http://localhost:11434）
- `--port`：Web UI 端口（默认：7860）
- `--model`：模型名称（local-qwen 表示本地模型，其他为 API 模型）
- `--api-key`：外部 API 密钥（如调用 DeepSeek 时必填）
- `--api-base`：外部 API 基础 URL

## Ollama 本地模型准备

如需自动拉取和配置本地 Qwen-7B 模型，可运行：

```bash
python scripts/setup_ollama.py
```

该脚本会自动检测 Ollama 安装、服务状态，并拉取所需模型。

## 常见问题

- 启动报错"无法连接到 Ollama 服务"：请确保 Ollama 已安装并启动，可手动打开 Ollama 应用或运行 `python scripts/setup_ollama.py`。
- 需要调用外部模型时，请在 Web UI 配置 API Key 和 Base URL。
- 如遇到 API 连接问题，请检查网络连接和 API 密钥是否正确。

## 目录结构说明

```
vertex/
├── src/
│   ├── app.py              # 主应用入口
│   ├── native_client.py    # 本地 Ollama 客户端
│   ├── model_client.py     # 通用 API 客户端
│   ├── langchain_client.py # LangChain 客户端
│   ├── chat_util.py        # 聊天历史格式化工具
│   └── utils/
│       └── logger.py       # 日志工具
├── scripts/
│   └── setup_ollama.py     # Ollama 环境与模型自动配置脚本
├── requirements.txt
├── setup.py
└── README.md
```

## 开发计划

- [ ] 支持更多本地模型（如 LLaMA、Mistral 等）
- [ ] 添加知识库检索功能
- [ ] 支持文档上传和分析
- [ ] 增加图表生成功能
- [ ] 提供 API 服务接口

## 贡献指南

欢迎提交 Pull Request 或 Issue 来帮助改进项目。贡献前请先查看现有 Issue，确保不会重复工作。