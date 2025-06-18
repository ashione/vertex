# 文档更新功能

## 概述

RAG系统现在支持智能的文档更新功能，可以检测文档内容的变化并自动更新索引，确保知识库始终保持最新状态。

## 功能特性

### 1. 智能更新检测
- 基于文件修改时间检测文档变化
- 支持内容哈希比较，避免重复索引
- 自动识别新增、更新和未变化的文档

### 2. 增量更新
- 只处理发生变化的文档
- 保持未变化文档的索引不变
- 提高更新效率，减少计算资源消耗

### 3. 元数据管理
- 记录文件修改时间、文件大小等元数据
- 支持文档来源追踪
- 便于调试和监控

## 使用方法

### 基本用法

```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 创建RAG系统
rag_system = UnifiedRAGSystem()

# 首次索引文档
doc_files = ["doc1.txt", "doc2.txt"]
rag_system.index_documents(doc_files)

# 更新文档内容后，重新索引（检测更新）
rag_system.index_documents(doc_files, update_existing=True)
```

### 参数说明

`index_documents` 方法支持以下参数：

- `documents`: 文档列表，可以是文件路径或文档内容
- `force_reindex`: 是否强制重新索引，默认False
- `update_existing`: 是否更新已存在的文档，默认True

### 更新模式

1. **首次索引** (`update_existing=False`):
   ```python
   # 完全重新索引，忽略现有文档
   rag_system.index_documents(doc_files, force_reindex=True)
   ```

2. **智能更新** (`update_existing=True`):
   ```python
   # 检测变化并更新，跳过未变化的文档
   rag_system.index_documents(doc_files, update_existing=True)
   ```

3. **跳过更新** (`update_existing=False`):
   ```python
   # 如果已有文档，完全跳过索引
   rag_system.index_documents(doc_files, update_existing=False)
   ```

## 更新检测机制

### 1. 文件修改时间检测
系统会记录每个文档的修改时间，当重新索引时：
- 比较当前文件修改时间与索引中的记录
- 如果时间差异超过1秒，认为文档已更新
- 自动重新处理更新的文档

### 2. 内容哈希去重
- 使用MD5哈希算法计算文档内容
- 相同内容的文档不会重复索引
- 支持跨文件路径的内容去重

### 3. 元数据记录
每个索引的文档都包含以下元数据：
- `source`: 文档来源路径
- `mtime`: 文件修改时间
- `file_size`: 文件大小
- `chunk_index`: 分块索引
- `total_chunks`: 总分块数

## 实际应用场景

### 1. 文档管理系统
```python
# 定期扫描文档目录，自动更新索引
import os
import time

def auto_update_docs(doc_dir, rag_system):
    """自动更新文档索引"""
    doc_files = []
    for root, dirs, files in os.walk(doc_dir):
        for file in files:
            if file.endswith(('.txt', '.md', '.pdf')):
                doc_files.append(os.path.join(root, file))
    
    # 智能更新
    rag_system.index_documents(doc_files, update_existing=True)
    print("文档索引已更新")

# 每小时更新一次
while True:
    auto_update_docs("/path/to/docs", rag_system)
    time.sleep(3600)
```

### 2. 版本控制集成
```python
# 与Git等版本控制系统集成
import subprocess

def get_modified_files():
    """获取Git中修改的文件"""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n')

# 只索引修改的文档
modified_files = get_modified_files()
if modified_files:
    rag_system.index_documents(modified_files, update_existing=True)
```

### 3. 实时监控
```python
# 监控文件变化并实时更新
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DocUpdateHandler(FileSystemEventHandler):
    def __init__(self, rag_system):
        self.rag_system = rag_system
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            print(f"检测到文件变化: {event.src_path}")
            self.rag_system.index_documents([event.src_path], update_existing=True)

# 设置文件监控
observer = Observer()
observer.schedule(DocUpdateHandler(rag_system), "/path/to/docs", recursive=True)
observer.start()
```

## 性能优化

### 1. 批量更新
```python
# 批量处理多个文档，提高效率
doc_files = ["doc1.txt", "doc2.txt", "doc3.txt"]
rag_system.index_documents(doc_files, update_existing=True)
```

### 2. 增量更新策略
- 系统会自动跳过未变化的文档
- 只对变化的文档进行向量化和索引
- 显著减少更新时间和计算资源

### 3. 内存管理
- 更新过程中及时释放不需要的内存
- 支持大文档的分块处理
- 避免内存溢出问题

## 监控和调试

### 1. 统计信息
```python
# 获取向量数据库统计信息
stats = rag_system.get_vector_db_stats()
print(f"总文档数: {stats['total_documents']}")
print(f"唯一文档数: {stats['unique_documents']}")
```

### 2. 更新日志
系统会记录详细的更新日志：
- 新增文档数量
- 跳过的重复文档数量
- 更新的文档数量
- 处理时间

### 3. 错误处理
```python
try:
    rag_system.index_documents(doc_files, update_existing=True)
except Exception as e:
    print(f"更新失败: {e}")
    # 可以回滚到之前的版本
```

## 最佳实践

1. **定期更新**: 建议定期运行更新，而不是每次文档变化都立即更新
2. **备份索引**: 重要数据建议定期备份向量索引
3. **监控资源**: 注意监控磁盘空间和内存使用情况
4. **测试更新**: 在生产环境部署前，先在测试环境验证更新功能

## 故障排除

### 常见问题

1. **更新不生效**
   - 检查文件修改时间是否正确
   - 确认文件路径是否一致
   - 验证文档内容是否真正发生变化

2. **性能问题**
   - 考虑批量处理而不是单个文件更新
   - 检查磁盘I/O性能
   - 监控内存使用情况

3. **索引损坏**
   - 删除索引文件重新构建
   - 检查磁盘空间是否充足
   - 验证文件权限设置 