# 中英文双语提示词功能

## 概述

Vertex Flow 深度研究工作流现在支持中英文双语提示词，用户可以根据需要选择使用中文或英文提示词进行分析。这个功能提供了更好的本地化体验，同时保持了分析的专业性和准确性。

## 功能特性

### 🌍 双语支持
- **英文提示词**: 提供专业的英文分析指导
- **中文提示词**: 提供本地化的中文分析指导
- **动态切换**: 支持在运行时切换语言

### 🔧 技术实现
- **语言参数**: 通过 `language` 参数控制提示词语言
- **提示词管理**: 统一的 `DeepResearchPrompts` 类管理双语提示词
- **格式化支持**: 支持变量替换和提示词格式化

### 📋 支持的阶段
所有深度研究阶段都支持中英文双语：

1. **主题分析** (Topic Analysis)
2. **研究规划** (Research Planning)
3. **信息收集** (Information Collection)
4. **深度分析** (Deep Analysis)
5. **交叉验证** (Cross Validation)
6. **总结报告** (Summary Report)

## 使用方法

### 1. 基本使用

```python
from vertex_flow.prompts.deep_research import DeepResearchPrompts

# 创建英文提示词管理器
en_prompts = DeepResearchPrompts(language="en")

# 创建中文提示词管理器
zh_prompts = DeepResearchPrompts(language="zh")

# 获取提示词
en_system_prompt = en_prompts.get_topic_analysis_system_prompt()
zh_system_prompt = zh_prompts.get_topic_analysis_system_prompt()
```

### 2. 动态语言切换

```python
# 创建提示词管理器
prompts = DeepResearchPrompts(language="en")

# 切换到中文
prompts.set_language("zh")

# 获取切换后的提示词
zh_prompt = prompts.get_topic_analysis_system_prompt()
```

### 3. 工作流集成

```python
# 在工作流中使用
def create_workflow(self, input_data: Dict[str, Any]) -> Workflow:
    # 获取语言设置
    language = input_data.get("language", "en")
    
    # 创建提示词管理器
    prompts = DeepResearchPrompts(language=language)
    
    # 使用对应语言的提示词
    system_prompt = prompts.get_topic_analysis_system_prompt()
    user_prompt = prompts.get_topic_analysis_user_prompt()
```

### 4. Gradio 界面使用

在 Gradio 界面中，用户可以通过语言选择组件选择提示词语言：

```python
# 语言选择组件
current_language = gr.Radio(
    choices=[("English", "en"), ("中文", "zh")],
    value="en",
    label="提示词语言",
    info="选择提示词的语言，影响分析结果的输出语言",
)

# 在事件处理中使用
def handle_start_research(topic, save_inter, save_final, stream_mode, format_mode, language):
    # 传入语言参数
    for result in app.start_research(topic, save_inter, save_final, stream_mode, language):
        # 处理结果
        pass
```

## 提示词质量对比

### 长度对比

| 阶段 | 英文系统 | 中文系统 | 英文用户 | 中文用户 |
|------|----------|----------|----------|----------|
| 主题分析 | 2644 | 967 | 352 | 94 |
| 研究规划 | 3297 | 991 | 297 | 89 |
| 信息收集 | 3154 | 880 | 246 | 78 |

### 质量特性

✅ **结构完整性**: 两种语言都包含完整的分析框架和输出格式
✅ **专业性**: 都提供专业的研究分析指导
✅ **可操作性**: 都强调具体、可操作的分析要求
✅ **证据导向**: 都要求提供具体的事实、数据和案例支持
✅ **格式化支持**: 都支持变量替换和提示词格式化

## 配置选项

### 语言选项

- `"en"`: 英文提示词（默认）
- `"zh"`: 中文提示词

### 默认设置

```python
# 默认使用英文
prompts = DeepResearchPrompts()  # language="en"

# 指定中文
prompts = DeepResearchPrompts(language="zh")
```

## 最佳实践

### 1. 语言选择建议

- **英文提示词**: 适合国际化的研究项目，与英文模型配合效果更好
- **中文提示词**: 适合中文用户，提供更本地化的分析体验

### 2. 工作流配置

```python
# 在工作流中支持动态语言切换
class DeepResearchWorkflow:
    def __init__(self, vertex_service, model=None, language="en"):
        self.language = language
        self.prompts = DeepResearchPrompts(language=language)
    
    def create_workflow(self, input_data: Dict[str, Any]) -> Workflow:
        # 获取语言设置，优先使用输入数据中的语言
        language = input_data.get("language", self.language)
        self.prompts.set_language(language)
        
        # 使用对应语言的提示词
        system_prompt = self.prompts.get_topic_analysis_system_prompt()
        user_prompt = self.prompts.get_topic_analysis_user_prompt()
```

### 3. 用户界面设计

- 提供清晰的语言选择选项
- 说明语言选择对分析结果的影响
- 保持界面的一致性和易用性

## 技术细节

### 提示词管理类

```python
class DeepResearchPrompts(BasePromptTemplate):
    def __init__(self, language: str = "en"):
        self.language = language.lower()
        if self.language not in ["en", "zh"]:
            self.language = "en"
    
    def get_available_languages(self) -> List[str]:
        return ["en", "zh"]
    
    def set_language(self, language: str):
        if language.lower() in ["en", "zh"]:
            self.language = language.lower()
```

### 提示词获取方法

每个阶段都有对应的中英文提示词获取方法：

```python
def get_topic_analysis_system_prompt(self) -> str:
    if self.language == "zh":
        return "中文系统提示词内容..."
    else:
        return "English system prompt content..."

def get_topic_analysis_user_prompt(self) -> str:
    if self.language == "zh":
        return "中文用户提示词内容..."
    else:
        return "English user prompt content..."
```

## 扩展性

### 添加新语言

要添加新的语言支持，需要：

1. 在 `get_available_languages()` 中添加新语言代码
2. 为每个提示词方法添加新语言的分支
3. 更新语言验证逻辑

### 自定义提示词

用户可以继承 `DeepResearchPrompts` 类来自定义提示词：

```python
class CustomPrompts(DeepResearchPrompts):
    def get_topic_analysis_system_prompt(self) -> str:
        if self.language == "zh":
            return "自定义中文提示词..."
        else:
            return "Custom English prompt..."
```

## 总结

中英文双语提示词功能为 Vertex Flow 深度研究工作流提供了更好的本地化支持，用户可以根据需要选择使用中文或英文提示词进行分析。这个功能不仅提高了用户体验，还保持了分析的专业性和准确性。

通过统一的提示词管理类和动态语言切换机制，系统可以灵活地适应不同用户的需求，为深度研究分析提供更加个性化和专业化的服务。 