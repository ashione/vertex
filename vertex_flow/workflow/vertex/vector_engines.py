import abc
import hashlib
from typing import Any, Dict, List, Optional
import os

import dashvector

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger()


class Doc:
    def __init__(self, vector, id: str = None, fields: Dict[str, Any] = None):
        self._vector = vector
        self._id = id
        self._fields = fields

    @property
    def id(self):
        return self._id

    @property
    def vector(self):
        return self._vector

    @property
    def fields(self):
        return self._fields


class VectorEngine(metaclass=abc.ABCMeta):
    def __init__(self, api_key, endpoint, index_name=None):
        self._api_key = api_key
        self._endpoint = endpoint
        if not index_name:
            logger.info("No index name provided, using default index name")
            self._index_name = "default"
        else:
            self._index_name = index_name

        self._index_map = {}

    @property
    def index_name(self):
        logger.info(f"index name is {self._index_name}")
        return self._index_name

    def get_index(self, index_name=None):
        """
        获取指定名称的索引。

        如果索引名称在_index_map中已存在，则直接返回对应的索引。
        否则，创建一个新的索引，并将其添加到_index_map中，然后返回。

        参数:
        index_name (str): 索引的名称，如果未提供，则默认为None。

        返回:
        index: 返回找到或新创建的索引。
        """

        index_name = index_name or self._index_name
        # 检查索引名称是否已存在于索引映射中
        if index_name in self._index_map:
            return self._index_map[index_name]

        # 如果索引名称不存在，创建新的索引并添加到索引映射中
        self._index_map[index_name] = self._index(index_name)

        # 返回新创建的索引
        return self._index_map[index_name]

    def put_index(self, index_name, index_client=None):
        if not index_client:
            self.get_index(index_name)
            logger.info(f"get index {index_name} if index_client is None")
            return

        if index_name in self._index_map:
            logger.warning(f"index {index_name} already exists")
            return

        self._index_map[index_name] = index_client
        logger.warning(f"put index {index_name}")

    @abc.abstractmethod
    def _index(self, index_name=None):
        pass

    @abc.abstractmethod
    def create_index(self, index_name, index_options=None):
        pass

    @abc.abstractmethod
    def delete_index(self, index_name):
        pass

    @abc.abstractmethod
    def search(self, query, index_name=None, include_vector=True, top_k=3, filter=None):
        """
        搜索索引的抽象方法。

        此方法应实现以提供在指定索引内的搜索功能，允许用户查询索引并检索最相关的结果。该方法支持检索最相关的 top_k 个结果，并可选地包括查询结果的向量表示。

        参数:
        - index_name: 要搜索的索引名称。此参数允许方法识别要操作的具体索引。
        - query: 要执行的查询。这可以是字符串、查询对象或具体实现期望的其他形式。
        - include_vector: 布尔值，表示是否包括查询结果的向量表示。默认为 True。这允许用户根据其应用场景决定是否需要向量信息。
        - top_k: 返回的最相关结果的数量。默认为 3。此参数允许用户指定他们希望接收的最相关结果的数量。
        - filter: 可选的过滤条件。默认为 None。此参数允许用户指定额外的条件来过滤搜索结果，从而缩小搜索范围并提高效率。

        返回值:
        该方法在其签名中未指定返回类型，但实现应返回与查询匹配的搜索结果，如果 include_vector 为 True，则可能包括向量表示。
        """
        pass

    @abc.abstractmethod
    def insert(self, docs, index_name=None):
        pass


class DashVector(VectorEngine):
    def __init__(self, api_key, endpoint, index_name=None):
        super().__init__(api_key, endpoint, index_name)

        self._client = dashvector.Client(api_key=api_key, endpoint=endpoint)
        # 判断client是否创建成功
        if self._client:
            logger.info("create dash vector client success!")
        else:
            logger.warning("failed to create dash vector client!")
            return
        logger.info(f"Get index info of {index_name}")
        self.put_index(self._index_name, self._client.get(self._index_name))

    def _index(self, index_name=None):
        """
        获取指定名称的索引信息。

        如果没有提供index_name参数，那么将使用实例初始化时设置的_index_name属性作为索引名称。
        该方法通过调用_client的get方法来获取索引信息。
        DashVector的每一个cluster并没有一个default的collection。

        参数:
        index_name (str, optional): 索引的名称。默认为None。

        返回:
        调用_client.get方法返回的索引信息。
        """
        # 如果传入的index_name为空，则使用实例的_index_name属性
        if not index_name:
            index_name = self._index_name
        # 调用_client的get方法，传入索引名称，返回索引信息
        logger.info(f"Get index info of {index_name}")
        return self._client.get(index_name)

    def insert(self, docs, index_name=None):
        """
        插入文档到向量索引

        Args:
            docs: 文档列表或单个文档
            index_name: 索引名称
        """
        if not isinstance(docs, list):
            docs = [docs]

        # 获取索引
        index = self.get_index(index_name)

        # 准备插入数据
        vectors = []
        for doc in docs:
            if isinstance(doc, dict):
                if "vector" in doc:
                    vectors.append(doc["vector"])
                elif "embedding" in doc:
                    vectors.append(doc["embedding"])
                else:
                    raise ValueError(f"文档字典缺少vector或embedding字段: {doc}")
            elif isinstance(doc, Doc):
                vectors.append(doc.vector)
            elif isinstance(doc, (list, tuple)) and all(isinstance(x, (int, float)) for x in doc):
                vectors.append(doc)
            else:
                raise ValueError(f"不支持的文档类型: {type(doc)}")

        if vectors:
            # 插入向量
            index.insert(vectors)
            logger.info(f"插入了 {len(vectors)} 个文档")

    def search(
        self,
        query,
        index_name: str = None,
        output_fields: List[str] = None,
        include_vector=False,
        top_k=3,
        filter=None,
    ):
        logger.info(f"search from {index_name}.")
        try:
            # 根据向量或者主键进行相似性检索 + 条件过滤
            result = self.get_index(index_name).query(
                query,  # 向量检索，也可设置主键检索
                topk=top_k,
                filter=filter,  # 条件过滤，仅对age > 18的Doc进行相似性检索
                output_fields=output_fields,  # 仅返回name、age这2个Field
                include_vector=include_vector,
            )
            logger.info(f"result : {result},{type(result)}")
            return result
        except BaseException as E:
            logger.warning(f"search failed: {E}")
            raise E

    def create_index(self, index_name, index_options=None):
        """
        创建一个新的索引。

        参数:
        index_name (str): 索引的名称。
        index_type (str, optional): 索引的类型，默认为 "default"。
        index_options (dict, optional): 索引的选项，默认为 None。

        返回:
        bool: 创建成功返回 True，否则返回 False。
        """

        if self._client.get(index_name):
            logger.warning(f"index {index_name} already exists")
            return True
        # 从index_options中提取所需的参数
        if index_options:
            dimension = index_options.get("dimension", 1024)
            metric = index_options.get("metric", "cosine")
            dtype = index_options.get("dtype", float)
            fields_schema = index_options.get("fields_schema", None)
            timeout = index_options.get("timeout", -1)
        else:
            dimension = 1024
            metric = "cosine"
            dtype = float
            fields_schema = None
            timeout = -1

        try:
            response = self._client.create(
                index_name,
                dimension=dimension,
                metric=metric,
                dtype=dtype,
                fields_schema=fields_schema,
                timeout=timeout,
            )
            if response.code == 0:
                logger.info(f"Index {index_name} created successfully.")
                self.put_index(index_name, self._client.get(index_name))
                return True
            else:
                logger.error(f"Failed to create index {index_name}. Response: {response}")
                return False
        except Exception as e:
            logger.error(f"Exception occurred while creating index {index_name}: {e}")
            return False

    def delete_index(self, index_name):
        """
        删除一个现有的索引。

        参数:
        index_name (str): 索引的名称。

        返回:
        bool: 删除成功返回 True，否则返回 False。
        """
        try:
            response = self._client.delete(index_name)
            if response.code == 0:
                logger.info(f"Index {index_name} deleted successfully.")
                if index_name in self._index_map:
                    del self._index_map[index_name]
                return True
            else:
                logger.error(f"Failed to delete index {index_name}. Response: {response}")
                return False
        except Exception as e:
            logger.error(f"Exception occurred while deleting index {index_name}: {e}")
            return False


class LocalVectorEngine(VectorEngine):
    """本地向量引擎，使用FAISS进行向量存储和检索"""

    def __init__(self, index_name: str = "default", dimension: int = 384, persist_dir: str = None):
        """
        初始化本地向量引擎
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            persist_dir: 持久化目录
        """
        super().__init__(api_key=None, endpoint=None, index_name=index_name)
        
        self.dimension = dimension
        self.persist_dir = persist_dir or os.path.join(os.getcwd(), "vector_db")
        
        try:
            import faiss
            import hashlib
            
            # 确保持久化目录存在
            os.makedirs(self.persist_dir, exist_ok=True)
            
            # 构建文件路径
            self.index_file = os.path.join(self.persist_dir, f"{index_name}.faiss")
            self.meta_file = os.path.join(self.persist_dir, f"{index_name}_meta.pkl")
            
            # 尝试加载现有索引
            if self._load_index():
                logger.info(f"加载现有索引: {index_name}, 包含 {len(self.documents)} 个文档")
            else:
                # 创建新索引
                self.index = faiss.IndexFlatIP(dimension)  # 使用内积相似度
                self.documents = []  # 存储文档内容
                self.doc_ids = []    # 存储文档ID
                self.content_hashes = {}  # 存储文档内容哈希值，用于去重
                logger.info(f"创建新索引: {index_name}, 维度: {dimension}")
                
        except ImportError:
            raise ImportError("请安装faiss-cpu: pip install faiss-cpu")
    
    def _generate_doc_id_from_path(self, file_path: str) -> str:
        """
        根据文件路径生成文档ID
        
        Args:
            file_path: 文件路径
            
        Returns:
            生成的文档ID
        """
        import os
        import hashlib
        
        # 获取文件名（不含扩展名）
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 生成路径的哈希值（用于确保唯一性）
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        
        # 组合文件名和哈希值
        doc_id = f"{file_name}_{path_hash}"
        
        return doc_id

    def _get_document_by_hash(self, content_hash: str) -> Optional[Dict]:
        """根据内容哈希获取文档信息"""
        if content_hash in self.content_hashes:
            doc_info = self.content_hashes[content_hash]
            doc_id = doc_info['id']
            # 查找文档在列表中的索引
            try:
                idx = self.doc_ids.index(doc_id)
                return {
                    'id': doc_id,
                    'content': self.documents[idx],
                    'index': idx,
                    'metadata': doc_info.get('metadata', {})
                }
            except ValueError:
                return None
        return None

    def _load_index(self):
        """加载现有索引"""
        try:
            import faiss
            import pickle
            import os
            
            if os.path.exists(self.index_file) and os.path.exists(self.meta_file):
                # 加载FAISS索引
                self.index = faiss.read_index(self.index_file)
                
                # 加载元数据
                with open(self.meta_file, 'rb') as f:
                    meta_data = pickle.load(f)
                    self.documents = meta_data.get('documents', [])
                    self.doc_ids = meta_data.get('doc_ids', [])
                    self.content_hashes = meta_data.get('content_hashes', {})
                
                return True
            return False
        except Exception as e:
            logger.warning(f"加载索引失败: {e}")
            return False
    
    def _save_index(self):
        """保存索引到本地文件"""
        try:
            import faiss
            import pickle
            
            # 保存FAISS索引
            faiss.write_index(self.index, self.index_file)
            
            # 保存元数据
            meta_data = {
                'documents': self.documents,
                'doc_ids': self.doc_ids,
                'content_hashes': self.content_hashes
            }
            with open(self.meta_file, 'wb') as f:
                pickle.dump(meta_data, f)
            
            logger.info(f"索引已保存到: {self.persist_dir}")
            
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def _generate_content_hash(self, content: str) -> str:
        """生成文档内容的哈希值"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, content: str) -> bool:
        """检查文档内容是否已存在"""
        content_hash = self._generate_content_hash(content)
        return content_hash in self.content_hashes
    
    def _check_file_updates(self, documents: List[str]) -> Dict[str, Any]:
        """
        检查文件更新情况
        
        Args:
            documents: 文档路径列表
            
        Returns:
            更新信息字典
        """
        import os
        from pathlib import Path
        
        update_info = {
            'new_files': [],
            'updated_files': [],
            'unchanged_files': [],
            'file_hashes': {}
        }
        
        for doc_path in documents:
            if not os.path.exists(doc_path):
                continue
                
            # 读取文件内容
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"无法读取文件 {doc_path}: {e}")
                continue
            
            # 生成内容哈希
            content_hash = self._generate_content_hash(content)
            update_info['file_hashes'][doc_path] = content_hash
            
            # 检查文件是否已存在
            existing_doc = self._get_document_by_hash(content_hash)
            
            if existing_doc:
                # 检查文件路径是否匹配（如果元数据中包含路径信息）
                existing_metadata = existing_doc.get('metadata', {})
                existing_path = existing_metadata.get('source', '')
                
                if existing_path == doc_path:
                    # 相同路径，检查文件修改时间
                    file_mtime = os.path.getmtime(doc_path)
                    existing_mtime = existing_metadata.get('mtime', 0)
                    
                    if abs(file_mtime - existing_mtime) < 1:  # 1秒内的差异认为是相同
                        update_info['unchanged_files'].append(doc_path)
                    else:
                        update_info['updated_files'].append(doc_path)
                else:
                    # 不同路径但内容相同，标记为未变化
                    update_info['unchanged_files'].append(doc_path)
            else:
                # 新文件
                update_info['new_files'].append(doc_path)
        
        return update_info
    
    def _index(self, index_name=None):
        """获取索引（本地实现中直接返回self）"""
        return self
    
    def create_index(self, index_name, index_options=None):
        """创建索引（本地实现中已创建）"""
        logger.info(f"索引 {index_name} 已创建")
    
    def delete_index(self, index_name):
        """删除索引"""
        try:
            import os
            
            # 删除文件
            if os.path.exists(self.index_file):
                os.remove(self.index_file)
            if os.path.exists(self.meta_file):
                os.remove(self.meta_file)
            
            # 清空内存
            self.index = None
            self.documents = []
            self.doc_ids = []
            
            logger.info(f"索引 {index_name} 已删除")
            
        except Exception as e:
            logger.error(f"删除索引失败: {e}")
    
    def insert(self, docs, index_name=None):
        """
        插入文档到向量索引，支持去重和更新检测
        
        Args:
            docs: 文档列表或单个文档
            index_name: 索引名称（本地实现中忽略）
        """
        if not isinstance(docs, list):
            docs = [docs]
        
        vectors = []
        inserted_count = 0
        skipped_count = 0
        updated_count = 0
        
        # 记录开始处理
        logger.info(f"开始处理 {len(docs)} 个文档的向量存储")
        
        for doc in docs:
            if isinstance(doc, dict):
                # 处理包含向量和元数据的字典
                content = doc.get("content", "")
                doc_id = doc.get("id", f"doc_{len(self.doc_ids)}")
                metadata = doc.get("metadata", {})
                
                # 检查是否重复
                if self._is_duplicate(content):
                    # 检查是否需要更新（基于内容哈希）
                    existing_doc = self._get_document_by_hash(self._generate_content_hash(content))
                    if existing_doc:
                        existing_id = existing_doc['id']
                        existing_metadata = existing_doc.get('metadata', {})
                        existing_path = existing_metadata.get('source', '')
                        current_path = metadata.get('source', '')
                        
                        # 检查文件路径是否发生变化
                        if existing_path != current_path and current_path:
                            # 文件名发生变化，需要更新
                            logger.info(f"文件名发生变化: {existing_path} -> {current_path}")
                            
                            # 更新文档ID和元数据
                            doc_id = self._generate_doc_id_from_path(current_path)
                            doc['id'] = doc_id
                            
                            # 标记为更新
                            updated_count += 1
                        else:
                            # 相同路径，检查是否需要强制更新
                            if metadata.get("force_update", False):
                                logger.debug(f"强制更新文档: {doc_id}")
                                updated_count += 1
                            else:
                                # 减少重复文档的日志输出
                                skipped_count += 1
                                continue
                else:
                    # 新文档，生成基于路径的ID
                    if metadata.get('source'):
                        doc_id = self._generate_doc_id_from_path(metadata['source'])
                        doc['id'] = doc_id
                
                if "vector" in doc:
                    vectors.append(doc["vector"])
                    self.documents.append(content)
                    self.doc_ids.append(doc_id)
                    # 记录内容哈希
                    content_hash = self._generate_content_hash(content)
                    self.content_hashes[content_hash] = {
                        'id': doc_id,
                        'metadata': metadata
                    }
                    inserted_count += 1
                elif "embedding" in doc:
                    # EmbeddingVertex的输出格式
                    vectors.append(doc["embedding"])
                    self.documents.append(content)
                    self.doc_ids.append(doc_id)
                    # 记录内容哈希
                    content_hash = self._generate_content_hash(content)
                    self.content_hashes[content_hash] = {
                        'id': doc_id,
                        'metadata': metadata
                    }
                    inserted_count += 1
                else:
                    raise ValueError(f"文档字典缺少vector或embedding字段: {doc}")
            elif isinstance(doc, Doc):
                content = doc.fields.get('content', '')
                
                # 检查是否重复
                if self._is_duplicate(content):
                    skipped_count += 1
                    continue
                
                vectors.append(doc.vector)
                self.documents.append(content)
                self.doc_ids.append(doc.id)
                # 记录内容哈希
                content_hash = self._generate_content_hash(content)
                self.content_hashes[content_hash] = {
                    'id': doc.id,
                    'metadata': doc.fields.get('metadata', {})
                }
                inserted_count += 1
            elif isinstance(doc, (list, tuple)) and all(isinstance(x, (int, float)) for x in doc):
                # 对于纯向量，无法进行内容去重，直接插入
                vectors.append(doc)
                self.documents.append("")  # 空内容
                self.doc_ids.append(f"doc_{len(self.doc_ids)}")
                inserted_count += 1
            else:
                raise ValueError(f"不支持的文档类型: {type(doc)}")
        
        # 如果有新文档插入，或者有文档被更新，都要保存索引和meta
        if vectors or updated_count > 0:
            import numpy as np
            if vectors:
                vectors_array = np.array(vectors, dtype=np.float32)
                self.index.add(vectors_array)
            self._save_index()
            
            # 简化日志输出，只显示关键统计信息
            if inserted_count > 0 or updated_count > 0:
                logger.info(f"向量存储完成: 新增 {inserted_count} 个，更新 {updated_count} 个，跳过 {skipped_count} 个重复")
            else:
                logger.info(f"向量存储完成: 跳过 {skipped_count} 个重复文档")
        else:
            logger.info(f"向量存储完成: 跳过 {skipped_count} 个重复文档")
    
    def search(self, query, index_name=None, include_vector=False, top_k=3, filter=None):
        """
        搜索相似文档
        
        Args:
            query: 查询向量
            index_name: 索引名称（本地实现中忽略）
            include_vector: 是否包含向量
            top_k: 返回结果数量
            filter: 过滤条件（本地实现中忽略）
            
        Returns:
            搜索结果列表
        """
        import numpy as np
        
        if isinstance(query, str):
            # 如果是字符串，需要先转换为向量
            raise ValueError("查询必须是向量，请先使用EmbeddingVertex处理")
        
        query_vector = np.array([query], dtype=np.float32)
        scores, indices = self.index.search(query_vector, top_k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents):
                result = {
                    'id': self.doc_ids[idx] if idx < len(self.doc_ids) else f"doc_{idx}",
                    'content': self.documents[idx],
                    'score': float(score)
                }
                if include_vector:
                    result['vector'] = query_vector[0].tolist()
                results.append(result)
        
        return results
    
    def get_stats(self):
        """获取索引统计信息"""
        return {
            'index_name': self.index_name,
            'dimension': self.dimension,
            'total_documents': len(self.documents),
            'unique_documents': len(self.content_hashes),
            'persist_dir': self.persist_dir,
            'index_file': self.index_file,
            'meta_file': self.meta_file
        } 