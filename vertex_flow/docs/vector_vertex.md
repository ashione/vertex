# VectorVertex 文档

## 概述

`VectorVertex` 是 VertexFlow 框架中专门用于向量操作的顶点类型系列。它包含一个抽象基类 `VectorVertex` 和两个具体实现：`VectorStoreVertex`（向量存储）和 `VectorQueryVertex`（向量查询）。这些顶点类型是构建向量数据库应用、语义搜索和相似度匹配系统的核心组件。

## 设计理念

### 1. 向量数据管理
- **统一接口**: 提供统一的向量存储和查询接口
- **引擎抽象**: 通过 `VectorEngine` 抽象不同的向量数据库
- **高效操作**: 优化向量的存储、索引和检索性能

### 2. 可扩展架构
- **插件化设计**: 支持多种向量数据库后端
- **灵活配置**: 支持不同的索引类型和相似度度量
- **批量操作**: 支持批量存储和查询优化

### 3. 语义搜索支持
- **多模态支持**: 支持文本、图像等多种数据类型的向量化
- **元数据管理**: 支持丰富的元数据存储和过滤
- **相似度计算**: 支持多种相似度度量方法

## 核心特性

### 1. 向量存储（VectorStoreVertex）
- 高效的向量数据存储
- 元数据关联和管理
- 批量插入优化
- 索引构建和维护

### 2. 向量查询（VectorQueryVertex）
- 快速相似度搜索
- Top-K 结果检索
- 元数据过滤
- 混合搜索支持

### 3. 向量引擎集成
- Faiss 本地向量库
- Pinecone 云向量数据库
- Weaviate 向量搜索引擎
- Chroma 嵌入式向量数据库

## 类设计

### VectorVertex（抽象基类）

```python
class VectorVertex(Vertex[T]):
    """向量操作的抽象基类"""
    
    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

### VectorStoreVertex（向量存储）

```python
class VectorStoreVertex(VectorVertex[T]):
    """向量存储顶点，用于存储向量数据"""
    
    def execute(self, inputs: Dict[str, Any], context: WorkflowContext[T]) -> Dict[str, Any]:
        """执行向量存储操作"""
```

### VectorQueryVertex（向量查询）

```python
class VectorQueryVertex(VectorVertex[T]):
    """向量查询顶点，用于查询相似向量"""
    
    def execute(self, inputs: Dict[str, Any], context: WorkflowContext[T]) -> Dict[str, Any]:
        """执行向量查询操作"""
```

### 参数配置

#### VectorStoreVertex 参数
- **vector_engine**: `VectorEngine` 实例，必需
- **collection_name**: 集合名称，默认为 "default"
- **batch_size**: 批处理大小，默认为 100
- **create_index**: 是否创建索引，默认为 True
- **index_type**: 索引类型（如 "IVF", "HNSW"）
- **metric**: 相似度度量（如 "cosine", "euclidean"）

#### VectorQueryVertex 参数
- **vector_engine**: `VectorEngine` 实例，必需
- **collection_name**: 集合名称，默认为 "default"
- **top_k**: 返回结果数量，默认为 10
- **threshold**: 相似度阈值，默认为 0.0
- **include_metadata**: 是否包含元数据，默认为 True
- **filter**: 元数据过滤条件

## 使用示例

### 基本向量存储

```python
from vertex_flow.workflow.vertex import VectorStoreVertex
from vertex_flow.engines.vector import FaissVectorEngine

# 创建向量引擎
vector_engine = FaissVectorEngine(
    dimension=1536,  # 向量维度
    index_type="IVF",  # 索引类型
    metric="cosine"  # 相似度度量
)

# 创建向量存储顶点
vector_store = VectorStoreVertex(
    id="document_store",
    name="文档向量存储",
    params={
        "vector_engine": vector_engine,
        "collection_name": "documents",
        "batch_size": 50
    }
)

# 存储单个向量
result = vector_store.execute(
    inputs={
        "vector": [0.1, 0.2, 0.3, ...],  # 1536维向量
        "metadata": {
            "title": "文档标题",
            "content": "文档内容",
            "author": "作者",
            "timestamp": "2024-01-01"
        },
        "id": "doc_001"
    },
    context=workflow_context
)

print(f"存储结果: {vector_store.output}")
```

### 批量向量存储

```python
# 批量存储多个向量
vectors_data = [
    {
        "vector": [0.1, 0.2, 0.3, ...],
        "metadata": {"title": "文档1", "category": "技术"},
        "id": "doc_001"
    },
    {
        "vector": [0.4, 0.5, 0.6, ...],
        "metadata": {"title": "文档2", "category": "科学"},
        "id": "doc_002"
    },
    {
        "vector": [0.7, 0.8, 0.9, ...],
        "metadata": {"title": "文档3", "category": "技术"},
        "id": "doc_003"
    }
]

batch_result = vector_store.execute(
    inputs={"vectors": vectors_data},
    context=context
)

print(f"批量存储了 {len(vectors_data)} 个向量")
```

### 向量查询

```python
from vertex_flow.workflow.vertex import VectorQueryVertex

# 创建向量查询顶点
vector_query = VectorQueryVertex(
    id="document_search",
    name="文档向量搜索",
    params={
        "vector_engine": vector_engine,
        "collection_name": "documents",
        "top_k": 5,
        "threshold": 0.7,
        "include_metadata": True
    }
)

# 执行相似度搜索
search_result = vector_query.execute(
    inputs={
        "query_vector": [0.15, 0.25, 0.35, ...],  # 查询向量
    },
    context=context
)

# 处理搜索结果
results = search_result["results"]
for i, result in enumerate(results):
    print(f"结果 {i+1}:")
    print(f"  相似度: {result['score']:.4f}")
    print(f"  标题: {result['metadata']['title']}")
    print(f"  类别: {result['metadata']['category']}")
    print()
```

### 带过滤条件的查询

```python
# 使用元数据过滤
filtered_query = VectorQueryVertex(
    id="filtered_search",
    params={
        "vector_engine": vector_engine,
        "collection_name": "documents",
        "top_k": 10,
        "filter": {
            "category": "技术",  # 只搜索技术类文档
            "timestamp": {"$gte": "2024-01-01"}  # 2024年以后的文档
        }
    }
)

filtered_result = filtered_query.execute(
    inputs={"query_vector": query_vector},
    context=context
)
```

## 与嵌入顶点集成

### 完整的文档存储工作流

```python
from vertex_flow.workflow.vertex import EmbeddingVertex, FunctionVertex
from vertex_flow.workflow.edge import Edge, Always
from vertex_flow.workflow.workflow import Workflow

# 1. 文本预处理顶点
def preprocess_document(inputs):
    doc = inputs["document"]
    
    # 清理和格式化文本
    cleaned_content = doc["content"].strip().replace("\n", " ")
    
    return {
        "text": cleaned_content,
        "metadata": {
            "title": doc["title"],
            "author": doc.get("author", "未知"),
            "category": doc.get("category", "其他"),
            "length": len(cleaned_content)
        },
        "doc_id": doc["id"]
    }

preprocess_vertex = FunctionVertex(
    id="preprocessor",
    task=preprocess_document
)

# 2. 文本嵌入顶点
embedding_vertex = EmbeddingVertex(
    id="embedder",
    params={"embedding_provider": embedding_provider},
    variables=[
        {
            "source_scope": "preprocessor",
            "source_var": "text",
            "local_var": "text"
        }
    ]
)

# 3. 向量存储顶点
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
        },
        {
            "source_scope": "preprocessor",
            "source_var": "metadata",
            "local_var": "metadata"
        },
        {
            "source_scope": "preprocessor",
            "source_var": "doc_id",
            "local_var": "id"
        }
    ]
)

# 构建存储工作流
storage_workflow = Workflow()
storage_workflow.add_vertex(preprocess_vertex)
storage_workflow.add_vertex(embedding_vertex)
storage_workflow.add_vertex(vector_store_vertex)

storage_workflow.add_edge(Edge(preprocess_vertex, embedding_vertex, Always()))
storage_workflow.add_edge(Edge(embedding_vertex, vector_store_vertex, Always()))

# 执行文档存储
document = {
    "id": "tech_001",
    "title": "机器学习基础",
    "content": "机器学习是人工智能的一个重要分支...",
    "author": "张三",
    "category": "技术"
}

storage_workflow.execute(inputs={"document": document})
```

### 语义搜索工作流

```python
# 查询嵌入顶点
query_embedding_vertex = EmbeddingVertex(
    id="query_embedder",
    params={"embedding_provider": embedding_provider}
)

# 向量查询顶点
vector_query_vertex = VectorQueryVertex(
    id="vector_searcher",
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

# 结果后处理顶点
def format_search_results(inputs):
    results = inputs["search_results"]
    
    formatted_results = []
    for result in results:
        formatted_results.append({
            "title": result["metadata"]["title"],
            "author": result["metadata"]["author"],
            "category": result["metadata"]["category"],
            "similarity": result["score"],
            "relevance": "高" if result["score"] > 0.8 else "中" if result["score"] > 0.6 else "低"
        })
    
    return {"formatted_results": formatted_results}

format_vertex = FunctionVertex(
    id="formatter",
    task=format_search_results,
    variables=[
        {
            "source_scope": "vector_searcher",
            "source_var": "results",
            "local_var": "search_results"
        }
    ]
)

# 构建搜索工作流
search_workflow = Workflow()
search_workflow.add_vertex(query_embedding_vertex)
search_workflow.add_vertex(vector_query_vertex)
search_workflow.add_vertex(format_vertex)

search_workflow.add_edge(Edge(query_embedding_vertex, vector_query_vertex, Always()))
search_workflow.add_edge(Edge(vector_query_vertex, format_vertex, Always()))

# 执行语义搜索
search_workflow.execute(inputs={"text": "深度学习算法"})

# 获取格式化的搜索结果
results = format_vertex.output["formatted_results"]
for result in results:
    print(f"标题: {result['title']}")
    print(f"作者: {result['author']}")
    print(f"相似度: {result['similarity']:.4f} ({result['relevance']})")
    print()
```

## 高级特性

### 1. 混合搜索

```python
class HybridSearchVertex(VectorQueryVertex):
    """混合搜索：结合向量搜索和关键词搜索"""
    
    def execute(self, inputs, context):
        # 向量搜索
        vector_results = super().execute(inputs, context)
        
        # 关键词搜索（如果提供了查询文本）
        if "query_text" in inputs:
            keyword_results = self._keyword_search(
                inputs["query_text"],
                inputs.get("keyword_top_k", 10)
            )
            
            # 合并和重排序结果
            combined_results = self._merge_results(
                vector_results["results"],
                keyword_results,
                alpha=inputs.get("alpha", 0.7)  # 向量搜索权重
            )
            
            self.output = {"results": combined_results}
        
        return self.output
    
    def _keyword_search(self, query_text, top_k):
        """关键词搜索实现"""
        # 这里可以集成 Elasticsearch 或其他全文搜索引擎
        # 简化示例
        return []
    
    def _merge_results(self, vector_results, keyword_results, alpha):
        """合并向量搜索和关键词搜索结果"""
        # 实现结果合并和重排序逻辑
        # alpha * vector_score + (1-alpha) * keyword_score
        return vector_results  # 简化返回
```

### 2. 增量索引更新

```python
class IncrementalVectorStoreVertex(VectorStoreVertex):
    """支持增量更新的向量存储"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_buffer = []
        self.buffer_size = self.params.get("buffer_size", 100)
    
    def execute(self, inputs, context):
        if "vector" in inputs:
            # 单个向量更新
            self.update_buffer.append({
                "vector": inputs["vector"],
                "metadata": inputs.get("metadata", {}),
                "id": inputs.get("id")
            })
        elif "vectors" in inputs:
            # 批量向量更新
            self.update_buffer.extend(inputs["vectors"])
        
        # 检查是否需要刷新缓冲区
        if len(self.update_buffer) >= self.buffer_size:
            self._flush_buffer()
        
        return super().execute(inputs, context)
    
    def _flush_buffer(self):
        """刷新缓冲区到向量引擎"""
        if self.update_buffer:
            # 批量更新向量引擎
            self.params["vector_engine"].batch_upsert(
                collection_name=self.params["collection_name"],
                vectors=self.update_buffer
            )
            
            print(f"刷新了 {len(self.update_buffer)} 个向量到索引")
            self.update_buffer.clear()
    
    def finalize(self):
        """最终化：刷新剩余缓冲区"""
        self._flush_buffer()
```

### 3. 多集合管理

```python
class MultiCollectionVectorVertex(VectorVertex):
    """多集合向量管理"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collections = self.params.get("collections", {})
    
    def create_collection(self, name, dimension, index_type="IVF"):
        """创建新集合"""
        self.params["vector_engine"].create_collection(
            name=name,
            dimension=dimension,
            index_type=index_type
        )
        self.collections[name] = {
            "dimension": dimension,
            "index_type": index_type,
            "created_at": datetime.now().isoformat()
        }
    
    def list_collections(self):
        """列出所有集合"""
        return list(self.collections.keys())
    
    def get_collection_stats(self, collection_name):
        """获取集合统计信息"""
        return self.params["vector_engine"].get_collection_stats(collection_name)
    
    def delete_collection(self, collection_name):
        """删除集合"""
        self.params["vector_engine"].delete_collection(collection_name)
        if collection_name in self.collections:
            del self.collections[collection_name]
```

### 4. 向量索引优化

```python
class OptimizedVectorStoreVertex(VectorStoreVertex):
    """优化的向量存储"""
    
    def execute(self, inputs, context):
        # 执行基本存储
        result = super().execute(inputs, context)
        
        # 检查是否需要重建索引
        if self._should_rebuild_index():
            self._rebuild_index()
        
        return result
    
    def _should_rebuild_index(self):
        """判断是否需要重建索引"""
        stats = self.params["vector_engine"].get_collection_stats(
            self.params["collection_name"]
        )
        
        # 如果向量数量增长超过阈值，重建索引
        threshold = self.params.get("rebuild_threshold", 10000)
        return stats.get("vector_count", 0) % threshold == 0
    
    def _rebuild_index(self):
        """重建索引以优化性能"""
        print("开始重建向量索引...")
        
        self.params["vector_engine"].rebuild_index(
            collection_name=self.params["collection_name"],
            index_type=self.params.get("index_type", "IVF"),
            metric=self.params.get("metric", "cosine")
        )
        
        print("向量索引重建完成")
```

## 向量引擎集成

### Faiss 本地引擎

```python
from vertex_flow.engines.vector import FaissVectorEngine

# 创建 Faiss 引擎
faiss_engine = FaissVectorEngine(
    dimension=1536,
    index_type="IVF",  # 或 "HNSW", "Flat"
    metric="cosine",   # 或 "euclidean", "inner_product"
    nlist=100,         # IVF 参数
    nprobe=10          # 查询参数
)

# 使用 Faiss 引擎的向量顶点
faiss_store = VectorStoreVertex(
    id="faiss_store",
    params={
        "vector_engine": faiss_engine,
        "collection_name": "faiss_collection"
    }
)
```

### Pinecone 云引擎

```python
from vertex_flow.engines.vector import PineconeVectorEngine

# 创建 Pinecone 引擎
pinecone_engine = PineconeVectorEngine(
    api_key="your-pinecone-api-key",
    environment="us-west1-gcp",
    index_name="your-index-name"
)

# 使用 Pinecone 引擎的向量顶点
pinecone_store = VectorStoreVertex(
    id="pinecone_store",
    params={
        "vector_engine": pinecone_engine,
        "collection_name": "pinecone_collection"
    }
)
```

### Weaviate 引擎

```python
from vertex_flow.engines.vector import WeaviateVectorEngine

# 创建 Weaviate 引擎
weaviate_engine = WeaviateVectorEngine(
    url="http://localhost:8080",
    api_key="your-weaviate-api-key",  # 可选
    additional_headers={}  # 可选
)

# 使用 Weaviate 引擎的向量顶点
weaviate_store = VectorStoreVertex(
    id="weaviate_store",
    params={
        "vector_engine": weaviate_engine,
        "collection_name": "Document",  # Weaviate 类名
        "schema": {
            "class": "Document",
            "properties": [
                {"name": "title", "dataType": ["string"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "category", "dataType": ["string"]}
            ]
        }
    }
)
```

## 性能优化

### 1. 批处理优化

```python
class BatchOptimizedVectorStore(VectorStoreVertex):
    """批处理优化的向量存储"""
    
    def execute(self, inputs, context):
        if "vectors" in inputs:
            vectors = inputs["vectors"]
            batch_size = self.params.get("batch_size", 100)
            
            # 根据向量维度动态调整批大小
            if vectors and len(vectors[0]["vector"]) > 1000:
                batch_size = max(10, batch_size // 2)
            
            # 分批处理
            results = []
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                batch_result = self._process_batch(batch)
                results.extend(batch_result)
            
            self.output = {"stored_count": len(results), "results": results}
            return self.output
        
        return super().execute(inputs, context)
    
    def _process_batch(self, batch):
        """处理单个批次"""
        return self.params["vector_engine"].batch_insert(
            collection_name=self.params["collection_name"],
            vectors=[item["vector"] for item in batch],
            metadatas=[item.get("metadata", {}) for item in batch],
            ids=[item.get("id") for item in batch]
        )
```

### 2. 查询优化

```python
class OptimizedVectorQuery(VectorQueryVertex):
    """优化的向量查询"""
    
    def execute(self, inputs, context):
        # 查询预处理
        query_vector = inputs["query_vector"]
        
        # 向量标准化
        if self.params.get("normalize_query", True):
            query_vector = self._normalize_vector(query_vector)
        
        # 动态调整 top_k
        top_k = self._adjust_top_k(inputs.get("top_k", self.params.get("top_k", 10)))
        
        # 执行查询
        results = self.params["vector_engine"].query(
            collection_name=self.params["collection_name"],
            query_vector=query_vector,
            top_k=top_k,
            filter=inputs.get("filter", self.params.get("filter")),
            include_metadata=self.params.get("include_metadata", True)
        )
        
        # 后处理结果
        processed_results = self._postprocess_results(results)
        
        self.output = {"results": processed_results}
        return self.output
    
    def _normalize_vector(self, vector):
        """标准化向量"""
        import numpy as np
        vector = np.array(vector)
        norm = np.linalg.norm(vector)
        return (vector / norm).tolist() if norm > 0 else vector.tolist()
    
    def _adjust_top_k(self, requested_top_k):
        """动态调整 top_k"""
        # 根据集合大小调整
        stats = self.params["vector_engine"].get_collection_stats(
            self.params["collection_name"]
        )
        
        max_vectors = stats.get("vector_count", float('inf'))
        return min(requested_top_k, max_vectors)
    
    def _postprocess_results(self, results):
        """后处理查询结果"""
        threshold = self.params.get("threshold", 0.0)
        
        # 过滤低相似度结果
        filtered_results = [
            result for result in results 
            if result["score"] >= threshold
        ]
        
        # 添加相似度等级
        for result in filtered_results:
            score = result["score"]
            if score >= 0.9:
                result["similarity_level"] = "极高"
            elif score >= 0.8:
                result["similarity_level"] = "高"
            elif score >= 0.6:
                result["similarity_level"] = "中"
            else:
                result["similarity_level"] = "低"
        
        return filtered_results
```

### 3. 内存管理

```python
import gc
from typing import Generator

class MemoryEfficientVectorStore(VectorStoreVertex):
    """内存高效的向量存储"""
    
    def execute_stream(self, inputs, context) -> Generator:
        """流式处理大量向量"""
        if "vectors" in inputs:
            vectors = inputs["vectors"]
            batch_size = self.params.get("batch_size", 100)
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                
                # 处理批次
                batch_result = self._process_batch(batch)
                
                # 生成结果
                for j, result in enumerate(batch_result):
                    yield {
                        "index": i + j,
                        "id": batch[j].get("id"),
                        "status": "stored",
                        "result": result
                    }
                
                # 强制垃圾回收
                gc.collect()
    
    def _process_batch(self, batch):
        """处理单个批次"""
        return self.params["vector_engine"].batch_insert(
            collection_name=self.params["collection_name"],
            vectors=[item["vector"] for item in batch],
            metadatas=[item.get("metadata", {}) for item in batch],
            ids=[item.get("id") for item in batch]
        )
```

## 错误处理和监控

### 异常处理

```python
class RobustVectorVertex(VectorVertex):
    """健壮的向量顶点基类"""
    
    def execute(self, inputs, context):
        try:
            return super().execute(inputs, context)
        except Exception as e:
            error_type = type(e).__name__
            
            if "connection" in str(e).lower():
                # 连接错误
                logging.error(f"向量引擎连接失败: {e}")
                return self._handle_connection_error(inputs, context)
            elif "timeout" in str(e).lower():
                # 超时错误
                logging.warning(f"向量操作超时: {e}")
                return self._handle_timeout_error(inputs, context)
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                # 配额或限制错误
                logging.warning(f"向量服务限制: {e}")
                return self._handle_quota_error(inputs, context)
            else:
                # 其他错误
                logging.error(f"向量操作失败 ({error_type}): {e}")
                raise e
    
    def _handle_connection_error(self, inputs, context):
        """处理连接错误"""
        # 尝试重新连接
        try:
            self.params["vector_engine"].reconnect()
            return super().execute(inputs, context)
        except:
            return {"error": "向量引擎连接失败", "status": "failed"}
    
    def _handle_timeout_error(self, inputs, context):
        """处理超时错误"""
        # 返回部分结果或重试
        return {"error": "操作超时", "status": "timeout"}
    
    def _handle_quota_error(self, inputs, context):
        """处理配额错误"""
        # 等待或降级处理
        return {"error": "服务配额不足", "status": "quota_exceeded"}
```

### 性能监控

```python
import time
from collections import defaultdict

class MonitoredVectorVertex(VectorVertex):
    """带监控的向量顶点"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = defaultdict(list)
        self.operation_count = 0
    
    def execute(self, inputs, context):
        start_time = time.time()
        
        # 记录操作统计
        operation_type = "store" if isinstance(self, VectorStoreVertex) else "query"
        
        if operation_type == "store":
            vector_count = len(inputs.get("vectors", [inputs])) if "vectors" in inputs else 1
        else:
            vector_count = 1
        
        try:
            result = super().execute(inputs, context)
            
            # 记录成功指标
            execution_time = time.time() - start_time
            self.metrics["execution_times"].append(execution_time)
            self.metrics["vector_counts"].append(vector_count)
            self.metrics["success_count"] += 1
            self.operation_count += 1
            
            # 计算吞吐量
            throughput = vector_count / execution_time if execution_time > 0 else 0
            self.metrics["throughput"].append(throughput)
            
            logging.info(f"向量{operation_type}完成: {vector_count} 向量, {execution_time:.2f}s, {throughput:.2f} 向量/秒")
            
            return result
            
        except Exception as e:
            self.metrics["error_count"] += 1
            logging.error(f"向量{operation_type}失败: {e}")
            raise e
    
    def get_performance_stats(self):
        """获取性能统计"""
        if not self.metrics["execution_times"]:
            return {"message": "暂无性能数据"}
        
        import statistics
        
        return {
            "总操作次数": self.operation_count,
            "成功次数": self.metrics["success_count"],
            "失败次数": self.metrics["error_count"],
            "平均执行时间": statistics.mean(self.metrics["execution_times"]),
            "平均吞吐量": statistics.mean(self.metrics["throughput"]),
            "总处理向量数": sum(self.metrics["vector_counts"]),
            "成功率": self.metrics["success_count"] / self.operation_count * 100 if self.operation_count > 0 else 0
        }
```

## 最佳实践

### 1. 向量维度选择

```python
# 根据应用场景选择合适的向量维度

# 文本嵌入
TEXT_DIMENSIONS = {
    "openai_ada_002": 1536,
    "sentence_transformers_mini": 384,
    "sentence_transformers_base": 768,
    "sentence_transformers_large": 1024
}

# 图像嵌入
IMAGE_DIMENSIONS = {
    "clip_vit_b32": 512,
    "clip_vit_l14": 768,
    "resnet50": 2048
}

def choose_optimal_dimension(data_type, model_name, performance_requirement):
    """选择最优向量维度"""
    if data_type == "text":
        dimensions = TEXT_DIMENSIONS
    elif data_type == "image":
        dimensions = IMAGE_DIMENSIONS
    else:
        raise ValueError(f"不支持的数据类型: {data_type}")
    
    if model_name in dimensions:
        return dimensions[model_name]
    
    # 根据性能要求选择
    if performance_requirement == "speed":
        return min(dimensions.values())
    elif performance_requirement == "accuracy":
        return max(dimensions.values())
    else:
        return 768  # 默认中等维度
```

### 2. 索引类型选择

```python
def choose_index_type(vector_count, query_pattern, accuracy_requirement):
    """选择最优索引类型"""
    
    if vector_count < 10000:
        # 小数据集，使用精确搜索
        return "Flat"
    elif vector_count < 100000:
        # 中等数据集
        if accuracy_requirement == "high":
            return "HNSW"  # 高精度
        else:
            return "IVF"   # 平衡性能
    else:
        # 大数据集
        if query_pattern == "frequent":
            return "HNSW"  # 频繁查询
        else:
            return "IVF"   # 批量查询
```

### 3. 批处理策略

```python
def optimize_batch_size(vector_dimension, memory_limit_mb=1024):
    """优化批处理大小"""
    
    # 估算单个向量的内存使用（字节）
    vector_size_bytes = vector_dimension * 4  # float32
    metadata_size_bytes = 1024  # 估算元数据大小
    total_size_per_vector = vector_size_bytes + metadata_size_bytes
    
    # 计算最大批大小
    memory_limit_bytes = memory_limit_mb * 1024 * 1024
    max_batch_size = memory_limit_bytes // total_size_per_vector
    
    # 设置合理的范围
    return max(10, min(max_batch_size, 1000))
```

### 4. 查询优化

```python
def optimize_query_parameters(collection_size, accuracy_requirement):
    """优化查询参数"""
    
    if collection_size < 10000:
        return {
            "nprobe": collection_size // 100,  # IVF 参数
            "ef": 200,  # HNSW 参数
            "top_k_multiplier": 1.0
        }
    elif collection_size < 100000:
        if accuracy_requirement == "high":
            return {
                "nprobe": collection_size // 50,
                "ef": 400,
                "top_k_multiplier": 1.5
            }
        else:
            return {
                "nprobe": collection_size // 100,
                "ef": 200,
                "top_k_multiplier": 1.2
            }
    else:
        return {
            "nprobe": min(collection_size // 100, 1000),
            "ef": 500,
            "top_k_multiplier": 2.0
        }
```

## 常见问题

### Q: 如何选择合适的相似度度量？

A: 根据数据特性选择：

```python
SIMILARITY_METRICS = {
    "cosine": {
        "适用场景": ["文本嵌入", "标准化向量"],
        "特点": "忽略向量长度，关注方向",
        "推荐": "大多数文本应用"
    },
    "euclidean": {
        "适用场景": ["图像特征", "连续数值"],
        "特点": "考虑向量长度和方向",
        "推荐": "空间距离重要的场景"
    },
    "inner_product": {
        "适用场景": ["推荐系统", "协同过滤"],
        "特点": "向量长度有意义",
        "推荐": "评分预测"
    }
}
```

### Q: 如何处理向量维度不匹配？

A: 实现维度适配器：

```python
class DimensionAdapter:
    """向量维度适配器"""
    
    def __init__(self, target_dimension):
        self.target_dimension = target_dimension
    
    def adapt(self, vector):
        """适配向量维度"""
        current_dimension = len(vector)
        
        if current_dimension == self.target_dimension:
            return vector
        elif current_dimension > self.target_dimension:
            # 降维：截断或PCA
            return vector[:self.target_dimension]
        else:
            # 升维：零填充或插值
            padding = [0.0] * (self.target_dimension - current_dimension)
            return vector + padding
```

### Q: 如何实现向量数据的备份和恢复？

A: 实现备份机制：

```python
class VectorBackupVertex(VectorVertex):
    """向量数据备份顶点"""
    
    def backup_collection(self, collection_name, backup_path):
        """备份集合数据"""
        import pickle
        import os
        
        # 获取所有向量数据
        vectors = self.params["vector_engine"].export_collection(collection_name)
        
        # 保存到文件
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, 'wb') as f:
            pickle.dump(vectors, f)
        
        print(f"集合 {collection_name} 已备份到 {backup_path}")
    
    def restore_collection(self, collection_name, backup_path):
        """恢复集合数据"""
        import pickle
        
        # 从文件加载
        with open(backup_path, 'rb') as f:
            vectors = pickle.load(f)
        
        # 恢复到向量引擎
        self.params["vector_engine"].import_collection(collection_name, vectors)
        
        print(f"集合 {collection_name} 已从 {backup_path} 恢复")
```

## 总结

`VectorVertex` 系列是 VertexFlow 框架中处理向量数据的核心组件，提供了：

1. **完整的向量生命周期管理**: 从存储到查询的全流程支持
2. **多引擎支持**: 兼容主流向量数据库和搜索引擎
3. **高性能优化**: 批处理、索引优化和内存管理
4. **企业级特性**: 错误处理、监控和备份恢复
5. **灵活的扩展性**: 支持自定义索引类型和相似度度量

通过合理使用 `VectorVertex` 系列，可以构建高效、可扩展的向量搜索和语义匹配应用。