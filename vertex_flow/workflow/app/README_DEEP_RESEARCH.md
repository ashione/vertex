# 深度研究工作流 (Deep Research Workflow)

## 概述

深度研究工作流是一个基于代码构建的多阶段研究分析系统，专门用于对复杂主题进行全面、深入的研究和分析。该工作流通过六个连续的分析阶段，从主题分析到最终报告生成，提供系统性的研究方法和高质量的分析结果。

## 工作流架构

### 🔄 六个核心阶段

1. **主题分析 (Topic Analysis)**
   - 分析研究主题的核心内容
   - 确定研究范围和边界
   - 识别关键问题和研究维度
   - 预测研究过程中的挑战

2. **研究规划 (Research Planning)**
   - 制定详细的研究计划
   - 选择合适的研究方法和工具
   - 确定信息来源和数据渠道
   - 设计质量控制措施

3. **信息收集 (Information Collection)**
   - 系统性收集基础信息和背景资料
   - 梳理历史发展和现状分析
   - 收集技术细节和市场情况
   - 整理案例研究和专家观点

4. **深度分析 (Deep Analysis)**
   - 进行趋势分析和关联分析
   - 评估优势劣势和技术成熟度
   - 识别风险和影响因素
   - 发现创新机会和深层洞察

5. **交叉验证 (Cross Validation)**
   - 验证关键事实和数据准确性
   - 检查分析逻辑的合理性
   - 考虑反驳观点和替代解释
   - 评估证据强度和不确定性

6. **总结报告 (Summary Report)**
   - 整合所有研究成果
   - 撰写完整的研究报告
   - 提供实践建议和风险提示
   - 预测未来发展趋势

## 文件结构

```
vertex_flow/workflow/app/
├── deep_research_workflow.py    # 主要工作流实现
├── test_deep_research.py        # 测试脚本
└── README_DEEP_RESEARCH.md      # 本文档
```

## 核心组件

### DeepResearchWorkflow 类

主要的工作流构建类，负责创建和配置整个研究工作流。

```python
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow

# 创建工作流实例
workflow_builder = DeepResearchWorkflow(vertex_service)

# 构建工作流
input_data = {
    "content": "人工智能在医疗领域的应用",
    "env_vars": {},
    "user_vars": {},
    "stream": False
}
workflow = workflow_builder.create_workflow(input_data)
```

### 工厂函数

提供便捷的工作流创建方法：

```python
from vertex_flow.workflow.app.deep_research_workflow import create_deep_research_workflow

# 创建工作流构建函数
builder_func = create_deep_research_workflow(vertex_service)

# 使用构建函数创建工作流
workflow = builder_func(input_data)
```

## 使用方法

### 1. 通过 API 接口使用

工作流已注册到系统中，可以通过 HTTP API 调用：

```bash
# POST 请求到工作流端点
curl -X POST "http://localhost:8000/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "deep-research",
    "content": "区块链技术在金融科技中的应用",
    "env_vars": {},
    "user_vars": {},
    "stream": false
  }'
```

### 2. 直接在代码中使用

```python
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow

# 初始化服务
vertex_service = VertexFlowService("config/llm.yml")

# 创建工作流
workflow_builder = DeepResearchWorkflow(vertex_service)
input_data = {
    "content": "可持续能源技术的发展趋势",
    "stream": False
}

workflow = workflow_builder.create_workflow(input_data)

# 执行工作流
workflow.execute_workflow({}, stream=False)

# 获取结果
results = workflow.result()
print(results['sink']['final_report'])
```

### 3. 流式处理模式

支持实时流式输出，适合长时间运行的研究任务：

```python
input_data = {
    "content": "量子计算技术的发展现状",
    "stream": True  # 启用流式模式
}

workflow = workflow_builder.create_workflow(input_data)
workflow.execute_workflow({}, stream=True)

# 异步获取流式结果
async for result in workflow.astream("messages"):
    print(f"实时结果: {result['message']}")
```

## 配置说明

### 输入参数

- **content**: 研究主题（必需）
- **env_vars**: 环境变量字典（可选）
- **user_vars**: 用户变量字典（可选）
- **stream**: 是否启用流式模式（可选，默认 False）

### 输出结果

工作流的最终输出包含：

- **final_report**: 完整的研究报告
- **message**: 执行状态信息
- **research_topic**: 原始研究主题

## 测试

### 运行测试脚本

```bash
# 运行所有测试
python vertex_flow/workflow/app/test_deep_research.py

# 运行特定测试
python vertex_flow/workflow/app/test_deep_research.py --test creation
python vertex_flow/workflow/app/test_deep_research.py --test prompts
python vertex_flow/workflow/app/test_deep_research.py --test factory

# 指定配置文件
python vertex_flow/workflow/app/test_deep_research.py --config config/llm.yml
```

### 测试覆盖范围

- ✅ 工作流创建测试
- ✅ 提示词模板测试
- ✅ 工厂函数测试
- ⚠️ 工作流执行测试（需要 API 调用）

## 性能优化

### 1. 并行处理

虽然当前实现是顺序执行，但可以通过修改工作流结构实现部分并行处理：

```python
# 示例：并行执行信息收集的不同方面
info_collection_tech = LLMVertex(id="info_tech", ...)
info_collection_market = LLMVertex(id="info_market", ...)
info_collection_social = LLMVertex(id="info_social", ...)

# 并行连接
research_planning | info_collection_tech
research_planning | info_collection_market
research_planning | info_collection_social

# 汇聚到深度分析
info_collection_tech | deep_analysis
info_collection_market | deep_analysis
info_collection_social | deep_analysis
```

### 2. 缓存机制

对于相似的研究主题，可以实现结果缓存：

```python
import hashlib
import json

def get_cache_key(research_topic: str) -> str:
    """生成研究主题的缓存键"""
    return hashlib.md5(research_topic.encode()).hexdigest()

def cache_result(cache_key: str, result: dict):
    """缓存研究结果"""
    # 实现缓存逻辑
    pass
```

### 3. 模型选择

根据不同阶段的需求选择合适的模型：

```python
# 分析阶段使用更强的模型
deep_analysis = LLMVertex(
    id="deep_analysis",
    params={
        "model": "gpt-4",  # 使用更强的模型
        "temperature": 0.8,  # 提高创造性
        ...
    }
)

# 验证阶段使用更保守的设置
cross_validation = LLMVertex(
    id="cross_validation",
    params={
        "model": "gpt-3.5-turbo",  # 使用更经济的模型
        "temperature": 0.4,  # 降低随机性
        ...
    }
)
```

## 扩展开发

### 添加新的分析阶段

```python
# 添加竞争分析阶段
competitive_analysis = LLMVertex(
    id="competitive_analysis",
    params={
        "model": self.vertex_service.get_chatmodel(),
        "system": self._get_competitive_analysis_system_prompt(),
        "user": [self._get_competitive_analysis_user_prompt()],
        ENABLE_STREAM: stream_mode,
    }
)

# 插入到工作流中
information_collection | competitive_analysis
competitive_analysis | deep_analysis
```

### 自定义提示词

```python
class CustomDeepResearchWorkflow(DeepResearchWorkflow):
    def _get_topic_analysis_system_prompt(self) -> str:
        """自定义主题分析提示词"""
        return """
        你是一位专门研究 [特定领域] 的专家...
        """
```

### 集成外部工具

```python
from vertex_flow.workflow.tools.functions import FunctionTool

def web_search_tool(inputs, context=None):
    """网络搜索工具"""
    query = inputs.get("query", "")
    # 实现网络搜索逻辑
    return {"search_results": "..."}

# 添加到 LLM 顶点
llm_with_tools = LLMVertex(
    id="enhanced_analysis",
    params={...},
    tools=[
        FunctionTool(
            name="web_search",
            description="搜索最新信息",
            func=web_search_tool,
            schema={...}
        )
    ]
)
```

## 故障排除

### 常见问题

1. **工作流创建失败**
   - 检查 vertex_service 是否正确初始化
   - 确认配置文件路径正确
   - 验证模型配置是否有效

2. **执行超时**
   - 调整模型的 temperature 参数
   - 简化提示词内容
   - 考虑使用更快的模型

3. **结果质量不佳**
   - 优化提示词模板
   - 调整模型参数
   - 增加更多上下文信息

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看工作流状态
workflow.show_graph(include_dependencies=True)
print(workflow.status())

# 检查中间结果
for vertex_id, result in workflow.result().items():
    print(f"{vertex_id}: {result[:100]}...")
```

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 添加测试用例
4. 提交 Pull Request

## 许可证

本项目遵循项目主仓库的许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 参与讨论

---

**注意**: 本工作流需要配置有效的 LLM API 才能正常运行。请确保在 `config/llm.yml` 中正确配置了模型服务。