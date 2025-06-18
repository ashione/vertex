# RAG系统安装指南

本指南将帮助您安装RAG系统，**完全排除grpcio编译问题**，仅使用本地功能。

## 快速安装（推荐）

### 1. 使用安装脚本
```bash
# 运行自动安装脚本（排除grpcio）
./scripts/install_rag_deps.sh
```

### 2. 手动安装
```bash
# 使用uv安装（推荐，排除grpcio）
uv pip install sentence-transformers>=2.2.0
uv pip install faiss-cpu>=1.7.0
uv pip install numpy>=1.21.0
uv pip install PyPDF2>=3.0.0
uv pip install python-docx>=0.8.11
```

## 排除grpcio编译问题

### 问题说明
- **grpcio编译失败**: 在ARM架构（如M1/M2 Mac）上编译grpcio经常失败
- **dashvector依赖**: dashvector依赖grpcio，导致编译问题
- **解决方案**: 完全排除dashvector，仅使用本地RAG功能

### 本地RAG系统功能
排除grpcio后，本地RAG系统完全支持：
- ✅ 文本向量化（sentence-transformers）
- ✅ 本地向量存储（faiss-cpu）
- ✅ 文档分块和索引
- ✅ 相似度搜索
- ✅ PDF/DOCX文档处理
- ✅ 智能问答
- ❌ 云端向量存储（需要dashvector）

### 安装策略

#### 1. 最小化安装（推荐）
```bash
# 只安装核心依赖，完全避免编译
uv pip install sentence-transformers faiss-cpu numpy
```

#### 2. 完整本地功能
```bash
# 安装所有本地RAG功能
uv pip install sentence-transformers faiss-cpu numpy PyPDF2 python-docx
```

#### 3. 云端功能（可选，需要编译）
```bash
# 如果需要云端向量存储，手动安装（可能编译失败）
uv pip install dashvector
```

## 验证安装

运行验证脚本：
```bash
python -c "
import sentence_transformers
import faiss
import numpy
import PyPDF2
import docx

# 确认没有grpcio
try:
    import grpcio
    print('⚠️  警告: 检测到grpcio')
except ImportError:
    print('✅ 确认: 未安装grpcio，避免编译问题')

print('✅ 所有依赖安装成功！')
"
```

## 常见问题

### 1. grpcio编译失败
**错误信息**: `command '/usr/bin/c++' failed with exit code 1`

**解决方案**:
- ✅ 使用本指南的安装方法，完全排除grpcio
- ✅ 本地RAG功能完全可用，无需云端存储

### 2. faiss-cpu安装失败
**解决方案**:
```bash
# 尝试conda安装
conda install -c conda-forge faiss-cpu

# 或使用pip安装预编译版本
pip install faiss-cpu --no-build-isolation
```

### 3. sentence-transformers下载慢
**解决方案**:
```bash
# 使用国内镜像
uv pip install sentence-transformers -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 最小化安装

如果只需要基本功能，可以只安装核心依赖：
```bash
# 最小化安装（无grpcio）
uv pip install sentence-transformers faiss-cpu numpy
```

这样安装的RAG系统支持：
- ✅ 文本向量化
- ✅ 本地向量存储
- ✅ 文档分块
- ✅ 相似度搜索
- ❌ PDF/DOCX文档处理（需要额外安装PyPDF2和python-docx）

## 测试安装

安装完成后，运行测试：
```bash
cd vertex_flow/examples
python test_rag_simple.py
```

如果测试通过，说明安装完成！

## 使用示例

```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 创建RAG系统（仅本地功能）
rag_system = UnifiedRAGSystem()

# 索引文档
documents = [
    "这是一个测试文档，包含关于人工智能的信息。",
    "机器学习是人工智能的一个重要分支。"
]
rag_system.index_documents(documents)

# 查询
answer = rag_system.query("什么是人工智能？")
print(answer)
```

## 注意事项

1. **仅本地功能**: 此配置不支持云端向量存储
2. **无需API密钥**: 本地RAG系统完全离线工作
3. **性能良好**: faiss-cpu在本地提供优秀的向量搜索性能
4. **易于部署**: 无需外部服务，适合本地部署 