# Workflow Chat 应用

基于 Workflow LLM Vertex 的新一代聊天应用，提供统一配置系统和现代化界面。

## 🚀 特性

- **统一配置系统**: 支持多种 LLM 提供商
- **动态模型切换**: 实时切换不同的模型提供商
- **多模态支持**: 支持文本和图片URL输入
- **AI思考过程**: 支持DeepSeek R1等reasoning模型
- **流式输出**: 实时流式响应
- **工具调用**: 支持Function Tools
- **现代化界面**: 基于Gradio的Web界面

## 📋 配置结构

### 简化的配置格式

配置结构已简化，只使用 `enabled` 字段：

```yaml
llm:
  openrouter:
    sk: ${llm.openrouter.sk:-YOUR_API_KEY}
    enabled: true
    models:
      - name: deepseek/deepseek-chat-v3-0324:free
        enabled: true
      - name: google/gemini-2.5-pro
        enabled: false
```

### 配置说明

- **provider级别**: `enabled` 表示该提供商是否启用
- **model级别**: `enabled` 表示该模型是否可用
- **模型选择**: 用户选择时，系统自动选择该提供商下第一个 `enabled: true` 的模型

## 🛠️ 使用方法

### 启动应用

```bash
# 使用默认配置
uv run python -m vertex_flow.src.workflow_app

# 指定端口
uv run python -m vertex_flow.src.workflow_app --port 7860
```

### 界面功能

1. **聊天界面**: 支持文本输入和图片URL
2. **模型管理**: 实时显示和切换模型
3. **思考过程**: 启用/禁用AI推理过程显示
4. **工具管理**: 启用/禁用Function Tools
5. **本地模型**: Ollama模型管理

### Reasoning功能

支持显示AI的思考过程，让用户了解AI的推理步骤：

**支持的模型**:
- DeepSeek R1系列模型
- 其他支持reasoning输出的模型

**使用方法**:
1. 选择支持reasoning的模型（如`deepseek/deepseek-r1-0528:free`）
2. 在"🤔 思考过程"配置面板中：
   - 勾选"启用思考过程"
   - 可选择是否"显示思考过程"
3. 发送问题，查看AI的详细推理过程

**应用场景**:
- 数学问题求解
- 逻辑推理分析
- 复杂问题分解
- 学习AI思维模式

## 🔧 配置示例

```yaml
llm:
  openrouter:
    sk: your-api-key
    enabled: true
    models:
      - name: deepseek/deepseek-chat-v3-0324:free
        enabled: true
      - name: google/gemini-2.5-pro
        enabled: false
```

## 🔍 故障排除

### 常见问题

1. **模型切换失败**: 检查提供商和模型是否启用
2. **Ollama连接失败**: 确保服务运行在 `http://localhost:11434`
3. **图片处理失败**: 检查URL可访问性和格式支持

## 🔄 更新日志

### v1.0.0 (2025-06-21)
- ✅ 简化配置结构，移除 `default` 字段
- ✅ 只使用 `enabled` 字段表示模型状态
- ✅ 优化模型切换逻辑
- ✅ 改进用户界面显示

## 🎯 使用场景

### 1. 多模型对比
- 配置多个模型提供商
- 实时切换不同模型进行对比测试
- 评估不同模型的性能和效果

### 2. 本地开发
- 使用Ollama本地模型进行开发测试
- 避免API调用费用
- 保护隐私和数据安全

### 3. 生产部署
- 使用云端模型服务
- 配置高可用性和负载均衡
- 监控和日志记录

### 4. 工具集成
- 启用Function Tools进行复杂任务处理
- 集成命令行工具执行系统操作
- 扩展自定义工具功能

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个应用！

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/your-repo/localqwen.git
cd localqwen

# 安装依赖
uv sync

# 运行开发版本
uv run python -m vertex_flow.src.workflow_app --port 7860
```

### 测试
```bash
# 运行测试
uv run pytest vertex_flow/tests/

# 运行特定测试
uv run pytest vertex_flow/tests/test_workflow_app.py
```

---

**📝 文档版本**: v1.0.0  
**🔄 最后更新**: 2025-06-21  
**📋 维护者**: Vertex开发团队 