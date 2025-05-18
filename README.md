# Vertex Workflow

本项目是一个基于 Vertex Flow 的本地化大模型工作流系统，支持多种 LLM、嵌入、向量检索与重排序能力，适用于本地智能应用开发和流程自动化。

## 主要特性

- **灵活的工作流引擎**：支持自定义顶点（Vertex）、边（Edge）、条件分支、函数节点、LLM 节点等，满足复杂流程编排需求。
- **多模型支持**：可集成多种主流大语言模型（如 Qwen、OpenAI、BCE 等），并可灵活切换。
- **嵌入与向量检索**：内置 DashVector、BCEEmbedding、DashScopeEmbedding 等主流向量引擎与嵌入模型。
- **重排序能力**：支持 BCE 等主流重排序模型，提升检索结果相关性。
- **本地化部署**：所有核心能力均可本地运行，保护数据隐私，适合企业/个人本地智能应用开发。
- **兼容 Dify 工作流**：可直接加载 Dify 工作流定义，便于迁移与扩展。

## 目录结构

- `vertex_flow/`：核心框架代码
  - `src/`：应用入口与客户端示例
  - `workflow/`：工作流相关模块（顶点、边、执行器、嵌入、重排序等）
  - `utils/`：日志与工具函数
- `config/`：示例工作流与配置
- `scripts/`：辅助脚本

## 快速开始

1. 安装依赖

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```