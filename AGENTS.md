# 仓库贡献指南

## 项目结构与模块组织
- `vertex_flow/` —— 核心包：包含 CLI（`cli.py`）、工作流引擎（`workflow/`）、记忆后端（`memory/`）、工具库（`utils/`）、示例（`examples/`）以及测试（`tests/`）。
- `web_ui/` —— 可选的本地 Web 端资源。
- `scripts/` —— 发布、测试及辅助脚本（例如 `run_tests.sh`、`publish.py`）。
- `docker/` —— Docker 构建脚本与镜像资源。
- `docs/` —— 文档目录；`README.md` 为主要入口说明。

## 构建、测试与开发命令
- 开发安装：`uv sync --dev` 或 `pip install -e .[dev]`。
- 格式化/静态检查：`uv run black . && uv run isort . && uv run flake8`。
- 运行测试：`uv run pytest vertex_flow/tests -v --cov=vertex_flow` 或 `scripts/run_tests.sh`。
- 本地应用：`uv run python -m vertex_flow.cli workflow --port 7860 --host 0.0.0.0`（安装后可直接执行 `vertex workflow`）。
- 构建 wheel 包：`make wheel`（清理后执行 `python -m build --wheel`）。
- Docker：`make build` 然后 `make run`（默认监听 `http://localhost:7860`）。

## 代码风格与命名规范
- 目标 Python 版本 ≥ 3.9；使用 4 空格缩进；最大行宽 120。
- 统一使用 `black`（行宽 120）、`isort`（`black` profile）和 `flake8`（配置见 `.flake8` / `pyproject.toml`）。
- 命名约定：模块/函数用 `snake_case`，类用 `PascalCase`，常量用 `UPPER_SNAKE_CASE`。
- 公共 API 保持类型标注；复杂模块或函数补充简洁文档字符串。

## 测试规范
- 测试框架：`pytest` 搭配 `pytest-asyncio`，放置于 `vertex_flow/tests/`。
- 命名规则：文件 `test_*.py` 或 `*_test.py`；类 `Test*`；函数 `test_*`。
- 常用标记：`unit`、`integration`、`slow`、`asyncio`。示例：`uv run pytest -m "unit and not slow"`。
- 追求有意义的覆盖率；CI 关键路径必须覆盖；默认保持测试隔离且运行迅速。

## 提交与 PR 指南
- 提交信息使用祈使语，简洁说明“做了什么 + 为什么”。例如：`fix(memory): prevent duplicate assistant messages`。
- 关联问题请引用 `#123`；避免将机械性改动与逻辑改动混在同一提交。
- PR 需包含清晰描述、关联问题、测试计划及 `pytest` 结果；如涉及 UI，附带截图；行为变化需同步更新文档/示例。
- 在请求评审前确保本地所有格式化与测试全部通过。

## 安全与配置建议
- 切勿提交密钥；使用 `.env`（由 `python-dotenv` 加载）。
- 通过 CLI 初始化或检查配置：`vertex config init|check`。
- 开发环境优先使用本地向量存储；测试中涉及外部网络调用的部分请使用标记或跳过策略进行隔离。

## 项目核心模块注意事项
- 对话请始终使用中文，虽然生成内容可能包含多语言。
- 未经确认不要随意编写或生成与项目无关的测试代码；如需测试实现，请先取得同意。
- Python 项目统一使用 `uv` 运行、安装及管理依赖。
- `vertex_flow/workflow/chat.py` 负责和大模型交互；`vertex_flow/workflow/vertex/` 内的顶点负责框架层服务与工作流调度。实现时务必确保交互代码与框架逻辑解耦。
- 修改 `llm_vertex` 时同步检查 `mcp_llm_vertex` 是否需要同样调整。
- 修改流式模式（stream mode）时必须确保非流式模式行为不受影响。
- 工具（tool/function）相关逻辑请集中在 Tool Caller / Tool Manager 中，不要直接写入 `chat.py` 或 `llm_vertex.py`。

## 项目结构补充说明
- `scripts/`：启动、部署、Lint 等脚本。
- `docs/`：项目文档。
- `tests/`：测试用例。
- `docker/`：Docker 构建文件。
- `vertex_flow/`
  - `workflow/`：工作流核心实现。
  - `vertex/`：各类顶点组件。
  - `mcp/`：Model Context Protocol 相关实现。
  - `plugins/`：扩展插件。
    - `wechat/`：微信公众号插件（服务端/客户端，包含独立 Dockerfile）。
- `README.md`：项目介绍与使用说明。
