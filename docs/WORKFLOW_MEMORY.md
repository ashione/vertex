# Workflow Chat 会话记忆

本文介绍 `vertex_flow/src/workflow_app.py` 中的会话记忆功能：如何启用、使用不同的存储后端，以及在工作流聊天中利用历史上下文与长期摘要。

## 功能概览

- **读写顶点**：
  - `MemoryReaderVertex` 负责从指定的 `Memory` 后端读取最近会话记录和必要的 `ctx_*` 条目。
  - `MemVertex` 负责将当前轮的用户/助手消息写回记忆，并可在需要时配置 `SummaryRule` 执行摘要写入。
- **系统提示增强**：当记忆开启时，读取到的上下文会以 `[记忆提示]` 形式附加到系统提示，帮助模型理解用户长期目标或背景。
- **UI 回填**：如果页面刷新导致前端历史为空，后台会自动从记忆中补全，用户无需重复对话。

## 启用方式

### 命令行参数

```bash
python -m vertex_flow.src.workflow_app \
  --enable-memory \
  --memory-type inner        # inner | file | redis | rds | hybrid
  --memory-user demo-user    # 可选：自定义记忆用户 ID
  --memory-maxlen 200        # 每个用户保留的最近历史条数
```

- `inner`：纯内存实现，适合本地体验或单机测试（进程结束即丢失）。
- `file`：写入文件系统，适合轻量持久化。
- `redis`、`rds`、`hybrid`：需提前配置对应服务，可提供高并发或持久存储能力。详细架构见 [vertexflow_memory_design.md](vertexflow_memory_design.md)。

### Web UI 切换

在 Workflow Chat 界面右侧 **配置 → 💬 对话历史** 中勾选 **启用会话记忆** 即可，无需重启服务。

## 工作流程

1. **载入阶段**：当 UI 无历史记录时，应用调用 `MemoryReaderVertex` 获取最近会话。若成功，则自动更新聊天框并传递给 LLM 做上下文输入。
2. **提示增强**：读取的 `ctx_*` 数据会被整理后写入 `[记忆提示]` 段落，附加到系统提示中，使模型了解用户长期意图。
3. **写入阶段**：每轮对话结束后，`MemVertex` 将用户输入与模型输出写入记忆。默认仅存储原文，可通过配置 `SummaryRule` 扩展为摘要、分类等结构化信息。

## 高级配置与自定义

- **存储后端**：在命令行中指定 `--memory-type`，或扩展 `MemoryFactory` 以支持新的后端。
- **用户隔离**：通过 `--memory-user`（或登录上下文）为不同用户生成独立记忆。
- **历史条数**：`--memory-maxlen` 控制保留的最大消息数，与 UI 中的“保留对话轮次”共同决定读取长度。
- **摘要规则**：若需将长期目标或关键信息写入 `ctx`，可在应用初始化时为 `MemVertex` 提供 `rules=[SummaryRule(...)]`，示例可参考 `vertex_flow/tests/test_memory_workflow.py`。

## 常见问题

- **刷新页面后无历史**：确认“启用会话记忆”已勾选，并检查后端服务是否可访问。
- **连接失败**：使用持久化后端（Redis/RDS）时，请确保依赖已安装且环境变量配置正确。
- **日志排查**：将环境变量 `LOG_LEVEL` 设为 `DEBUG`，即可在控制台中看到读写记忆时的详细日志。

更多关于记忆模块的设计细节、存储格式与扩展方案，请参阅 [vertexflow_memory_design.md](vertexflow_memory_design.md)。

