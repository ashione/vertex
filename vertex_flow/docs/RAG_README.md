# 本地RAG工作流系统

基于vertex flow接口实现的本地检索增强生成（RAG）系统，支持多种文档格式和本地/云端组件。

## 功能特性

- **统一配置管理**: 与现有的LLM配置系统完全融合
- **本地优先**: 默认使用本地组件，无需API密钥
- **多种文档格式**: 支持TXT、MD、PDF、DOCX等格式
- **智能文档分块**: 自动进行文档分块和向量化
- **灵活的工作流**: 基于vertex flow的可视化工作流
- **云端扩展**: 支持DashScope、BCE等云端服务

## 系统架构

### 索引工作流
```
文档输入 → 文档处理 → 文档向量化 → 向量存储 → 完成
```

### 查询工作流
```
查询输入 → 查询向量化 → 向量检索 → 生成回答 → 输出答案
```

## 安装依赖

### 基础依赖
```bash
# 使用uv安装Python包
uv pip install sentence-transformers faiss-cpu
```

### 可选依赖（用于文档处理）
```bash
# PDF文档支持
uv pip install PyPDF2

# Word文档支持
uv pip install python-docx
```

## 配置说明

系统使用 `config/llm.yml` 配置文件，主要配置项包括：

### 嵌入模型配置
```yaml
embedding:
  # 本地嵌入模型（默认启用）
  local:
    enabled: true
    model_name: "all-MiniLM-L6-v2"
    dimension: 384
  
  # DashScope云端嵌入
  dashscope:
    enabled: false
    api-key: ${embedding.dashscope.api_key:-}
    model-name: text-embedding-v1
  
  # BCE云端嵌入
  bce:
    enabled: false
    api-key: ${embedding.bce.api_key:-}
    model-name: netease-youdao/bce-embedding-base_v1
```

### 向量存储配置
```yaml
vector:
  # 本地向量存储（默认启用）
  local:
    enabled: true
    dimension: 384
    index_name: "default"
  
  # DashVector云端存储
  dashvector:
    enabled: false
    api-key: ${vector.dashvector.api_key:sk-}
    endpoint: ${vector.dashvector.endpoint:-}
    cluster: vertex-vector
    collection: ${vector.dashvector.collection:-}
```

### 文档处理配置
```yaml
document:
  chunk_size: 1000      # 文档分块大小
  chunk_overlap: 200    # 分块重叠大小
  supported_formats: ["txt", "md", "pdf", "docx"]
```

### 检索配置
```yaml
retrieval:
  top_k: 3                    # 检索文档数量
  similarity_threshold: 0.7    # 相似度阈值
  rerank: false               # 是否启用重排序
```

## 使用方法

### 1. 基础使用

```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 创建RAG系统
rag_system = UnifiedRAGSystem()

# 构建工作流
rag_system.build_workflows()

# 索引文档
documents = [
    "这是第一个文档的内容...",
    "这是第二个文档的内容...",
    "/path/to/document.txt"
]
rag_system.index_documents(documents)

# 查询
answer = rag_system.query("你的问题")
print(answer)
```

### 2. 运行示例

```bash
# 运行交互式示例
cd vertex_flow/examples
python rag_example.py
```

### 3. 自定义配置

```python
# 使用自定义配置文件
rag_system = UnifiedRAGSystem("path/to/custom_config.yml")
```

## 工作流组件

### 文档处理顶点 (DocumentProcessorVertex)
- 支持多种文档格式加载
- 自动文档分块
- 元数据提取

### 嵌入顶点 (EmbeddingVertex)
- 本地sentence-transformers模型
- 支持云端DashScope/BCE服务
- 自动向量化

### 向量存储顶点 (VectorStoreVertex)
- 本地FAISS向量索引
- 支持云端DashVector服务
- 高效相似度搜索

### 向量查询顶点 (VectorQueryVertex)
- 语义相似度检索
- 可配置返回数量
- 支持过滤条件

### LLM顶点 (LLMVertex)
- 基于检索结果生成答案
- 支持多种LLM提供商
- 可自定义提示词

## 扩展功能

### 1. 添加新的嵌入模型

```python
class CustomEmbeddingProvider(TextEmbeddingProvider):
    def __init__(self, model_name: str):
        # 初始化自定义模型
        pass
    
    def embedding(self, text: str) -> Optional[List[float]]:
        # 实现向量化逻辑
        pass
```

### 2. 添加新的向量引擎

```python
class CustomVectorEngine(VectorEngine):
    def __init__(self, **kwargs):
        # 初始化自定义向量引擎
        pass
    
    def insert(self, docs, index_name=None):
        # 实现文档插入逻辑
        pass
    
    def search(self, query, **kwargs):
        # 实现搜索逻辑
        pass
```

### 3. 自定义文档处理器

```python
class CustomDocumentProcessor(FunctionVertex):
    def process_documents(self, inputs: Dict[str, Any], context=None):
        # 实现自定义文档处理逻辑
        pass
```

## 性能优化

### 1. 向量维度优化
- 根据文档特点选择合适的嵌入模型
- 平衡精度和性能

### 2. 分块策略优化
- 调整chunk_size和chunk_overlap
- 根据文档结构优化分块

### 3. 检索参数调优
- 调整top_k值
- 设置合适的相似度阈值

## 故障排除

### 常见问题

1. **依赖包安装失败**
   ```bash
   # 使用conda安装faiss
   conda install -c conda-forge faiss-cpu
   
   # 或使用pip安装CPU版本
   pip install faiss-cpu
   ```

2. **内存不足**
   - 减少chunk_size
   - 使用更小的嵌入模型
   - 分批处理文档

3. **向量维度不匹配**
   - 确保嵌入模型和向量引擎的维度一致
   - 检查配置文件中的dimension设置

### 日志调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看详细执行日志
rag_system.index_documents(documents)
```

## 最佳实践

1. **文档预处理**
   - 清理和标准化文档格式
   - 移除无关内容
   - 保持文档结构一致性

2. **配置管理**
   - 使用环境变量管理敏感信息
   - 为不同环境创建配置文件
   - 定期备份配置

3. **性能监控**
   - 监控索引构建时间
   - 跟踪查询响应时间
   - 优化资源使用

4. **安全考虑**
   - 本地处理敏感文档
   - 加密存储向量索引
   - 控制访问权限

## 许可证

本项目基于vertex flow项目，遵循相应的开源许可证。 