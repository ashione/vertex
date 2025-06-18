# 本地索引去重功能

## 概述

LocalVectorEngine 现在支持自动去重功能，可以避免重复索引相同内容的文档，提高索引效率并节省存储空间。

## 功能特性

### 1. 基于内容的去重
- 使用 MD5 哈希算法对文档内容进行哈希计算
- 在插入文档前检查内容是否已存在
- 自动跳过重复文档，避免重复索引

### 2. 持久化支持
- 去重信息与向量索引一起持久化存储
- 重启应用后仍能保持去重状态
- 支持多个索引的独立去重

### 3. 统计信息
- 提供总文档数和唯一文档数的统计
- 显示插入和跳过的文档数量
- 便于监控索引状态

## 使用方法

### 基本用法

```python
from vertex_flow.workflow.vertex.vector_engines import LocalVectorEngine

# 创建向量引擎
vector_engine = LocalVectorEngine(
    index_name="my_index",
    dimension=384,
    persist_dir="/path/to/vector_db"
)

# 插入文档（自动去重）
docs = [
    {
        "id": "doc1",
        "content": "这是第一个文档的内容",
        "embedding": [0.1] * 384
    },
    {
        "id": "doc2", 
        "content": "这是第二个文档的内容",
        "embedding": [0.2] * 384
    }
]

# 首次插入
vector_engine.insert(docs)
# 输出: 插入了 2 个新文档，跳过了 0 个重复文档

# 插入重复文档（内容相同）
duplicate_docs = [
    {
        "id": "doc1_duplicate",
        "content": "这是第一个文档的内容",  # 相同内容
        "embedding": [0.3] * 384  # 不同的向量
    }
]

# 重复文档会被自动跳过
vector_engine.insert(duplicate_docs)
# 输出: 没有新文档需要插入，跳过了 1 个重复文档
```

### 在RAG系统中使用

```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 创建RAG系统
rag_system = UnifiedRAGSystem()
rag_system.build_workflows()

# 索引文档（自动去重）
doc_files = ["doc1.txt", "doc2.txt", "doc3.txt"]
rag_system.index_documents(doc_files)

# 查看统计信息
stats = rag_system.get_vector_db_stats()
print(f"总文档数: {stats['total_documents']}")
print(f"唯一文档数: {stats['unique_documents']}")

# 再次索引相同文档（会被去重）
rag_system.index_documents(doc_files)
# 输出: 向量数据库中已有 X 个文档，跳过索引。使用 force_reindex=True 强制重新索引。
```

## 配置选项

### 持久化目录
```python
# 自定义持久化目录
vector_engine = LocalVectorEngine(
    index_name="my_index",
    dimension=384,
    persist_dir="/custom/path/to/vector_db"  # 自定义目录
)
```

### 强制重新索引
```python
# 在RAG系统中强制重新索引（忽略去重）
rag_system.index_documents(doc_files, force_reindex=True)
```

## 技术实现

### 去重算法
1. **内容哈希**: 使用 MD5 算法对文档内容进行哈希计算
2. **哈希存储**: 将内容哈希值与文档ID关联存储在内存中
3. **查重检查**: 插入前检查内容哈希是否已存在
4. **持久化**: 哈希映射与向量索引一起保存到本地文件

### 数据结构
```python
class LocalVectorEngine:
    def __init__(self, ...):
        self.content_hashes = {}  # 存储内容哈希映射
        self.documents = []       # 存储文档内容
        self.doc_ids = []         # 存储文档ID
        self.index = None         # FAISS索引
```

### 文件存储
- `{index_name}.faiss`: FAISS向量索引文件
- `{index_name}_meta.pkl`: 元数据文件（包含文档内容、ID和哈希映射）

## 性能考虑

### 优势
- **避免重复计算**: 跳过重复文档的向量化过程
- **节省存储空间**: 避免存储重复的向量数据
- **提高索引效率**: 减少不必要的索引操作

### 注意事项
- **内存使用**: 哈希映射会占用少量内存
- **哈希冲突**: 理论上存在MD5哈希冲突的可能性（极低）
- **内容敏感性**: 去重基于内容，相同内容的不同格式会被识别为重复

## 示例演示

运行去重功能演示：
```bash
uv run python vertex_flow/examples/deduplication_demo.py
```

运行RAG示例（包含去重演示）：
```bash
uv run python vertex_flow/examples/rag_example.py
```

## 故障排除

### 常见问题

1. **去重不生效**
   - 检查文档内容是否完全相同（包括空格、换行符等）
   - 确认使用的是LocalVectorEngine而不是其他向量引擎

2. **统计信息异常**
   - 检查持久化文件是否完整
   - 确认索引文件权限正确

3. **性能问题**
   - 大量文档时哈希计算可能影响性能
   - 考虑分批处理文档

### 调试信息
启用调试日志查看去重过程：
```python
import logging
logging.getLogger('vertex_flow.workflow.vertex.vector_engines').setLevel(logging.DEBUG)
```

## 更新日志

- **v1.0**: 初始版本，支持基本的基于内容的去重
- **v1.1**: 添加统计信息和持久化支持
- **v1.2**: 优化性能和内存使用 