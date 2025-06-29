# EmbeddingVertex 文档

> **注意**: 关于变量依赖和数据传递的详细说明，请参考 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 文档。

## 概述

`EmbeddingVertex` 是 VertexFlow 框架中专门用于文本嵌入（Text Embedding）的顶点类型。它继承自 `Vertex` 基类，提供了将文本转换为向量表示的功能，是构建语义搜索、相似度计算、聚类分析等应用的核心组件。

## 设计理念

### 1. 向量化抽象
- **文本到向量**: 将自然语言文本转换为数值向量表示
- **语义保持**: 保持文本的语义信息在向量空间中
- **标准化接口**: 提供统一的嵌入生成接口

### 2. 提供者无关
- **多模型支持**: 支持 OpenAI、Sentence Transformers、本地模型等
- **统一调用**: 通过 `TextEmbeddingProvider` 抽象不同的嵌入服务
- **配置灵活**: 支持不同的模型参数和配置

### 3. 批处理优化
- **批量处理**: 支持多文本批量嵌入生成
- **性能优化**: 减少 API 调用次数，提高处理效率
- **内存管理**: 智能管理大批量数据的内存使用

## 核心特性

### 1. 文本嵌入生成
- 单文本和批量文本嵌入
- 自动文本预处理
- 向量维度标准化

### 2. 多种输入格式
- 单个文本字符串
- 文本列表
- 结构化文档对象

### 3. 嵌入提供者集成
- OpenAI Embeddings API
- Sentence Transformers 本地模型
- 自定义嵌入服务

### 4. 缓存和优化
- 嵌入结果缓存
- 批处理优化
- 异步处理支持

## 类设计

### EmbeddingVertex

```python
class EmbeddingVertex(Vertex[T]):
    """文本嵌入顶点，将文本转换为向量表示"""
    
    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

### 参数配置

`params` 字典支持以下配置项：

- **embedding_provider**: `TextEmbeddingProvider` 实例，必需
- **batch_size**: 批处理大小，默认为 100
- **normalize**: 是否标准化向量，默认为 True
- **cache_embeddings**: 是否缓存嵌入结果，默认为 False
- **text_field**: 输入文本字段名，默认为 "text"
- **output_field**: 输出向量字段名，默认为 "embedding"

## 使用示例

### 基本文本嵌入

```python
from vertex_flow.workflow.vertex import EmbeddingVertex
from vertex_flow.providers.embedding import OpenAIEmbeddingProvider

# 创建嵌入提供者
embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-ada-002"
)

# 创建嵌入顶点
embedding_vertex = EmbeddingVertex(
    id="text_embedder",
    name="文本嵌入器",
    params={
        "embedding_provider": embedding_provider,
        "normalize": True
    }
)

# 执行单文本嵌入
result = embedding_vertex.execute(
    inputs={"text": "这是一个测试文本"},
    context=workflow_context
)

print(f"嵌入维度: {len(embedding_vertex.output['embedding'])}")
print(f"嵌入向量: {embedding_vertex.output['embedding'][:5]}...")  # 显示前5个维度
```

### 批量文本嵌入

```python
# 批量处理多个文本
texts = [
    "人工智能是计算机科学的一个分支",
    "机器学习是人工智能的核心技术",
    "深度学习是机器学习的重要方法",
    "自然语言处理应用广泛",
    "计算机视觉技术发展迅速"
]

batch_result = embedding_vertex.execute(
    inputs={"texts": texts},
    context=context
)

# 输出包含所有文本的嵌入向量
embeddings = batch_result["embeddings"]
print(f"处理了 {len(embeddings)} 个文本")
print(f"每个嵌入向量维度: {len(embeddings[0])}")
```

### 文档嵌入处理

```python
# 处理结构化文档
documents = [
    {
        "id": "doc1",
        "title": "人工智能概述",
        "content": "人工智能是模拟人类智能的技术...",
        "category": "技术"
    },
    {
        "id": "doc2",
        "title": "机器学习基础",
        "content": "机器学习是让计算机从数据中学习...",
        "category": "教育"
    }
]

# 配置文档嵌入顶点
doc_embedding_vertex = EmbeddingVertex(
    id="doc_embedder",
    name="文档嵌入器",
    params={
        "embedding_provider": embedding_provider,
        "text_field": "content",  # 指定要嵌入的字段
        "batch_size": 50
    }
)

result = doc_embedding_vertex.execute(
    inputs={"documents": documents},
    context=context
)

# 输出包含原文档信息和嵌入向量
embedded_docs = result["embedded_documents"]
for doc in embedded_docs:
    print(f"文档 {doc['id']}: 嵌入维度 {len(doc['embedding'])}")
```

### 使用本地模型

```python
from vertex_flow.providers.embedding import SentenceTransformerProvider

# 使用 Sentence Transformers 本地模型
local_provider = SentenceTransformerProvider(
    model_name="all-MiniLM-L6-v2",
    device="cpu"  # 或 "cuda" 如果有 GPU
)

local_embedding_vertex = EmbeddingVertex(
    id="local_embedder",
    name="本地嵌入器",
    params={
        "embedding_provider": local_provider,
        "batch_size": 32,
        "normalize": True
    }
)

# 本地模型通常处理速度更快
result = local_embedding_vertex.execute(
    inputs={"text": "本地模型嵌入测试"},
    context=context
)
```

### 多语言文本嵌入

```python
# 使用多语言模型
multilingual_provider = SentenceTransformerProvider(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

multilingual_vertex = EmbeddingVertex(
    id="multilingual_embedder",
    params={"embedding_provider": multilingual_provider}
)

# 处理多语言文本
multilingual_texts = [
    "Hello, how are you?",  # 英文
    "你好，你好吗？",        # 中文
    "Hola, ¿cómo estás?",   # 西班牙文
    "Bonjour, comment allez-vous?",  # 法文
]

result = multilingual_vertex.execute(
    inputs={"texts": multilingual_texts},
    context=context
)

# 多语言文本在同一向量空间中
embeddings = result["embeddings"]
print(f"处理了 {len(embeddings)} 种语言的文本")
```

## 高级特性

### 1. 嵌入缓存

```python
import hashlib
import pickle
import os

class CachedEmbeddingVertex(EmbeddingVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_dir = "./embedding_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, text):
        """生成文本的缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, cache_key):
        """从缓存加载嵌入"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def _save_to_cache(self, cache_key, embedding):
        """保存嵌入到缓存"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(embedding, f)
    
    def execute(self, inputs, context):
        if "text" in inputs:
            text = inputs["text"]
            cache_key = self._get_cache_key(text)
            
            # 尝试从缓存加载
            cached_embedding = self._load_from_cache(cache_key)
            if cached_embedding is not None:
                print(f"使用缓存的嵌入: {cache_key}")
                self.output = {"embedding": cached_embedding}
                return self.output
            
            # 生成新嵌入
            result = super().execute(inputs, context)
            
            # 保存到缓存
            self._save_to_cache(cache_key, result["embedding"])
            return result
        
        return super().execute(inputs, context)
```

### 2. 异步批处理

```python
import asyncio
from typing import List

class AsyncEmbeddingVertex(EmbeddingVertex):
    async def execute_async(self, inputs, context):
        """异步执行嵌入生成"""
        if "texts" in inputs:
            texts = inputs["texts"]
            embeddings = await self._batch_embed_async(texts)
            self.output = {"embeddings": embeddings}
            return self.output
        
        # 单文本异步处理
        text = inputs.get("text", "")
        embedding = await self._embed_async(text)
        self.output = {"embedding": embedding}
        return self.output
    
    async def _batch_embed_async(self, texts: List[str]):
        """异步批量嵌入"""
        batch_size = self.params.get("batch_size", 100)
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self.params["embedding_provider"].embed_async(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def _embed_async(self, text: str):
        """异步单文本嵌入"""
        return await self.params["embedding_provider"].embed_async([text])[0]
```

### 3. 相似度计算集成

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class SimilarityEmbeddingVertex(EmbeddingVertex):
    def execute(self, inputs, context):
        """生成嵌入并计算相似度"""
        result = super().execute(inputs, context)
        
        # 如果提供了参考文本，计算相似度
        if "reference_text" in inputs:
            ref_result = super().execute(
                {"text": inputs["reference_text"]}, 
                context
            )
            
            # 计算余弦相似度
            embedding1 = np.array(result["embedding"]).reshape(1, -1)
            embedding2 = np.array(ref_result["embedding"]).reshape(1, -1)
            
            similarity = cosine_similarity(embedding1, embedding2)[0][0]
            
            result["similarity"] = float(similarity)
            result["reference_embedding"] = ref_result["embedding"]
        
        self.output = result
        return result

# 使用示例
similarity_vertex = SimilarityEmbeddingVertex(
    id="similarity_embedder",
    params={"embedding_provider": embedding_provider}
)

result = similarity_vertex.execute(
    inputs={
        "text": "机器学习是人工智能的分支",
        "reference_text": "人工智能包含机器学习技术"
    },
    context=context
)

print(f"相似度: {result['similarity']:.4f}")
```

### 4. 文本预处理集成

```python
import re
from typing import List

class PreprocessedEmbeddingVertex(EmbeddingVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preprocessors = [
            self._clean_text,
            self._normalize_whitespace,
            self._remove_special_chars
        ]
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除 URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _remove_special_chars(self, text: str) -> str:
        """移除特殊字符（可选）"""
        # 保留中文、英文、数字和基本标点
        return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:]', '', text)
    
    def _preprocess_text(self, text: str) -> str:
        """应用所有预处理步骤"""
        for preprocessor in self.preprocessors:
            text = preprocessor(text)
        return text
    
    def execute(self, inputs, context):
        # 预处理输入文本
        if "text" in inputs:
            inputs["text"] = self._preprocess_text(inputs["text"])
        elif "texts" in inputs:
            inputs["texts"] = [self._preprocess_text(text) for text in inputs["texts"]]
        elif "documents" in inputs:
            text_field = self.params.get("text_field", "content")
            for doc in inputs["documents"]:
                if text_field in doc:
                    doc[text_field] = self._preprocess_text(doc[text_field])
        
        return super().execute(inputs, context)
```

## 与向量数据库集成

### 与 VectorStoreVertex 配合使用

```python
from vertex_flow.workflow.vertex import VectorStoreVertex
from vertex_flow.workflow.edge import Edge, Always
from vertex_flow.workflow.workflow import Workflow

# 创建嵌入顶点
embedding_vertex = EmbeddingVertex(
    id="embedder",
    params={"embedding_provider": embedding_provider}
)

# 创建向量存储顶点
vector_store_vertex = VectorStoreVertex(
    id="vector_store",
    params={
        "vector_engine": vector_engine,
        "collection_name": "documents"
    },
    variables=[
        {
            "source_scope": "embedder",
            "source_var": "embedding",
            "local_var": "vector"
        }
    ]
)

# 构建工作流
workflow = Workflow()
workflow.add_vertex(embedding_vertex)
workflow.add_vertex(vector_store_vertex)
workflow.add_edge(Edge(embedding_vertex, vector_store_vertex, Always()))

# 执行文档存储
workflow.execute(inputs={
    "text": "要存储的文档内容",
    "metadata": {"title": "文档标题", "author": "作者"}
})
```

### 语义搜索工作流

```python
from vertex_flow.workflow.vertex import VectorQueryVertex, FunctionVertex

# 查询嵌入顶点
query_embedding_vertex = EmbeddingVertex(
    id="query_embedder",
    params={"embedding_provider": embedding_provider}
)

# 向量查询顶点
vector_query_vertex = VectorQueryVertex(
    id="vector_query",
    params={
        "vector_engine": vector_engine,
        "collection_name": "documents",
        "top_k": 5
    },
    variables=[
        {
            "source_scope": "query_embedder",
            "source_var": "embedding",
            "local_var": "query_vector"
        }
    ]
)

# 结果处理顶点
def format_search_results(inputs):
    results = inputs["search_results"]
    formatted = []
    
    for result in results:
        formatted.append({
            "content": result["metadata"]["content"],
            "score": result["score"],
            "title": result["metadata"].get("title", "未知")
        })
    
    return {"formatted_results": formatted}

format_vertex = FunctionVertex(
    id="formatter",
    task=format_search_results,
    variables=[
        {
            "source_scope": "vector_query",
            "source_var": "results",
            "local_var": "search_results"
        }
    ]
)

# 构建语义搜索工作流
search_workflow = Workflow()
search_workflow.add_vertex(query_embedding_vertex)
search_workflow.add_vertex(vector_query_vertex)
search_workflow.add_vertex(format_vertex)

search_workflow.add_edge(Edge(query_embedding_vertex, vector_query_vertex, Always()))
search_workflow.add_edge(Edge(vector_query_vertex, format_vertex, Always()))

# 执行语义搜索
search_workflow.execute(inputs={"text": "机器学习算法"})
```

## 性能优化

### 1. 批处理优化

```python
class OptimizedEmbeddingVertex(EmbeddingVertex):
    def execute(self, inputs, context):
        """优化的批处理执行"""
        if "texts" in inputs:
            texts = inputs["texts"]
            batch_size = self.params.get("batch_size", 100)
            
            # 智能批处理：根据文本长度调整批大小
            avg_length = sum(len(text) for text in texts) / len(texts)
            if avg_length > 1000:  # 长文本
                batch_size = max(10, batch_size // 4)
            elif avg_length < 100:  # 短文本
                batch_size = min(500, batch_size * 2)
            
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.params["embedding_provider"].embed(batch)
                embeddings.extend(batch_embeddings)
            
            self.output = {"embeddings": embeddings}
            return self.output
        
        return super().execute(inputs, context)
```

### 2. 内存管理

```python
import gc
from typing import Generator

class MemoryEfficientEmbeddingVertex(EmbeddingVertex):
    def execute_generator(self, inputs, context) -> Generator:
        """生成器模式，节省内存"""
        if "texts" in inputs:
            texts = inputs["texts"]
            batch_size = self.params.get("batch_size", 100)
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.params["embedding_provider"].embed(batch)
                
                for j, embedding in enumerate(batch_embeddings):
                    yield {
                        "index": i + j,
                        "text": batch[j],
                        "embedding": embedding
                    }
                
                # 强制垃圾回收
                gc.collect()
```

### 3. 并行处理

```python
import concurrent.futures
from typing import List

class ParallelEmbeddingVertex(EmbeddingVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_workers = self.params.get("max_workers", 4)
    
    def _embed_batch(self, batch: List[str]):
        """嵌入单个批次"""
        return self.params["embedding_provider"].embed(batch)
    
    def execute(self, inputs, context):
        if "texts" in inputs:
            texts = inputs["texts"]
            batch_size = self.params.get("batch_size", 100)
            
            # 分割成批次
            batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
            
            # 并行处理批次
            embeddings = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_batch = {executor.submit(self._embed_batch, batch): batch for batch in batches}
                
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_embeddings = future.result()
                    embeddings.extend(batch_embeddings)
            
            self.output = {"embeddings": embeddings}
            return self.output
        
        return super().execute(inputs, context)
```

## 错误处理和监控

### 异常处理

```python
class RobustEmbeddingVertex(EmbeddingVertex):
    def execute(self, inputs, context):
        try:
            return super().execute(inputs, context)
        except Exception as e:
            error_type = type(e).__name__
            
            if "rate_limit" in str(e).lower():
                # API 限流错误
                logging.warning(f"嵌入服务限流: {e}")
                # 实现重试逻辑
                return self._retry_with_backoff(inputs, context)
            elif "timeout" in str(e).lower():
                # 超时错误
                logging.warning(f"嵌入服务超时: {e}")
                return self._handle_timeout(inputs, context)
            else:
                # 其他错误
                logging.error(f"嵌入生成失败 ({error_type}): {e}")
                raise e
    
    def _retry_with_backoff(self, inputs, context, max_retries=3):
        """带退避的重试机制"""
        import time
        
        for attempt in range(max_retries):
            try:
                time.sleep(2 ** attempt)  # 指数退避
                return super().execute(inputs, context)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logging.info(f"重试 {attempt + 1}/{max_retries}")
    
    def _handle_timeout(self, inputs, context):
        """处理超时情况"""
        # 返回零向量或默认值
        if "text" in inputs:
            dimension = self.params.get("dimension", 1536)  # 默认维度
            self.output = {"embedding": [0.0] * dimension}
        elif "texts" in inputs:
            dimension = self.params.get("dimension", 1536)
            self.output = {"embeddings": [[0.0] * dimension] * len(inputs["texts"])}
        
        return self.output
```

### 性能监控

```python
import time
from collections import defaultdict

class MonitoredEmbeddingVertex(EmbeddingVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = defaultdict(list)
    
    def execute(self, inputs, context):
        start_time = time.time()
        
        # 记录输入统计
        if "text" in inputs:
            text_count = 1
            total_chars = len(inputs["text"])
        elif "texts" in inputs:
            text_count = len(inputs["texts"])
            total_chars = sum(len(text) for text in inputs["texts"])
        else:
            text_count = 0
            total_chars = 0
        
        try:
            result = super().execute(inputs, context)
            
            # 记录成功指标
            execution_time = time.time() - start_time
            self.metrics["execution_times"].append(execution_time)
            self.metrics["text_counts"].append(text_count)
            self.metrics["char_counts"].append(total_chars)
            self.metrics["success_count"] += 1
            
            # 计算吞吐量
            throughput = text_count / execution_time if execution_time > 0 else 0
            self.metrics["throughput"].append(throughput)
            
            logging.info(f"嵌入生成完成: {text_count} 文本, {execution_time:.2f}s, {throughput:.2f} 文本/秒")
            
            return result
            
        except Exception as e:
            self.metrics["error_count"] += 1
            logging.error(f"嵌入生成失败: {e}")
            raise e
    
    def get_performance_stats(self):
        """获取性能统计"""
        if not self.metrics["execution_times"]:
            return {"message": "暂无性能数据"}
        
        import statistics
        
        return {
            "总执行次数": len(self.metrics["execution_times"]),
            "成功次数": self.metrics["success_count"],
            "失败次数": self.metrics["error_count"],
            "平均执行时间": statistics.mean(self.metrics["execution_times"]),
            "平均吞吐量": statistics.mean(self.metrics["throughput"]),
            "总处理文本数": sum(self.metrics["text_counts"]),
            "总处理字符数": sum(self.metrics["char_counts"])
        }
```

## 最佳实践

### 1. 选择合适的嵌入模型

```python
# 根据应用场景选择模型

# 通用英文场景
openai_provider = OpenAIEmbeddingProvider(
    model="text-embedding-ada-002"  # 性价比高
)

# 多语言场景
multilingual_provider = SentenceTransformerProvider(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# 中文场景
chinese_provider = SentenceTransformerProvider(
    model_name="shibing624/text2vec-base-chinese"
)

# 代码场景
code_provider = SentenceTransformerProvider(
    model_name="microsoft/codebert-base"
)

# 科学文献场景
scientific_provider = SentenceTransformerProvider(
    model_name="allenai/scibert_scivocab_uncased"
)
```

### 2. 文本预处理策略

```python
def preprocess_for_embedding(text: str, domain: str = "general") -> str:
    """根据领域优化文本预处理"""
    
    # 通用预处理
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # 标准化空白
    
    if domain == "code":
        # 代码文本预处理
        text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)  # 移除注释
        text = re.sub(r'\s+', ' ', text)  # 压缩空白
    elif domain == "academic":
        # 学术文本预处理
        text = re.sub(r'\[[0-9,\s]+\]', '', text)  # 移除引用标记
        text = re.sub(r'Fig\.|Figure|Table', '', text)  # 移除图表引用
    elif domain == "web":
        # 网页文本预处理
        text = re.sub(r'<[^>]+>', '', text)  # 移除HTML标签
        text = re.sub(r'http[s]?://\S+', '', text)  # 移除URL
    
    return text
```

### 3. 批处理优化

```python
def optimize_batch_size(texts: List[str], max_batch_size: int = 100) -> int:
    """根据文本特征优化批处理大小"""
    if not texts:
        return max_batch_size
    
    avg_length = sum(len(text) for text in texts) / len(texts)
    
    if avg_length > 2000:  # 长文本
        return min(10, max_batch_size)
    elif avg_length > 500:  # 中等文本
        return min(50, max_batch_size)
    else:  # 短文本
        return max_batch_size

# 在顶点中使用
class SmartBatchEmbeddingVertex(EmbeddingVertex):
    def execute(self, inputs, context):
        if "texts" in inputs:
            texts = inputs["texts"]
            optimal_batch_size = optimize_batch_size(texts)
            self.params["batch_size"] = optimal_batch_size
        
        return super().execute(inputs, context)
```

## 常见问题

### Q: 如何选择合适的嵌入维度？

A: 嵌入维度通常由模型决定，但可以考虑以下因素：
- **存储成本**: 更高维度需要更多存储空间
- **计算效率**: 更高维度的相似度计算更慢
- **精度要求**: 更高维度通常提供更好的语义表示

### Q: 如何处理不同长度的文本？

A: 大多数嵌入模型有最大长度限制：

```python
def truncate_text(text: str, max_length: int = 512) -> str:
    """截断文本到最大长度"""
    words = text.split()
    if len(words) <= max_length:
        return text
    return ' '.join(words[:max_length])

def chunk_long_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """将长文本分块"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        
        if i + chunk_size >= len(words):
            break
    
    return chunks
```

### Q: 如何评估嵌入质量？

A: 可以使用多种方法评估：

```python
def evaluate_embeddings(embeddings, labels=None):
    """评估嵌入质量"""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    import numpy as np
    
    embeddings = np.array(embeddings)
    
    # 聚类评估
    if len(embeddings) > 10:
        n_clusters = min(5, len(embeddings) // 2)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)
        silhouette = silhouette_score(embeddings, cluster_labels)
        
        print(f"聚类轮廓系数: {silhouette:.4f}")
    
    # 如果有标签，计算分类性能
    if labels is not None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        
        clf = LogisticRegression(random_state=42)
        scores = cross_val_score(clf, embeddings, labels, cv=5)
        print(f"分类准确率: {scores.mean():.4f} ± {scores.std():.4f}")
```

## 总结

`EmbeddingVertex` 是构建语义理解应用的核心组件，提供了：

1. **灵活的文本嵌入**: 支持多种模型和提供者
2. **高效的批处理**: 优化的批量处理和内存管理
3. **丰富的集成**: 与向量数据库和搜索系统无缝集成
4. **企业级特性**: 包括缓存、监控和错误处理
5. **可扩展性**: 支持自定义预处理和后处理

通过合理使用 `EmbeddingVertex`，可以构建强大的语义搜索、文档分析和智能推荐系统。