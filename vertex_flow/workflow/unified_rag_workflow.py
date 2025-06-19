#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置的RAG Workflow实现
基于vertex flow接口和统一配置实现的本地检索增强生成系统
"""

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from vertex_flow.workflow.utils import default_config_path

from ..utils.logger import LoggerUtil
from .chat import ChatModel
from .constants import SYSTEM, USER
from .rag_config import read_yaml_config_env_placeholder
from .service import EmbeddingType, VertexFlowService
from .vertex import (
    EmbeddingVertex,
    FunctionVertex,
    LLMVertex,
    SinkVertex,
    SourceVertex,
    VectorQueryVertex,
    VectorStoreVertex,
)
from .vertex.embedding_providers import LocalEmbeddingProvider, TextEmbeddingProvider
from .vertex.vector_engines import Doc, LocalVectorEngine, VectorEngine
from .workflow import Workflow, WorkflowContext

logging = LoggerUtil.get_logger()


class ResultFormatterVertex(FunctionVertex):
    """结果格式化顶点，用于格式化向量检索结果"""

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            id=id,
            name=name or "结果格式化",
            task=self.format_results,
            params=params or {},
            variables=variables or [],
        )

    def format_results(self, inputs: Dict[str, Any], context=None):
        """
        格式化向量检索结果

        Args:
            inputs: 包含检索结果的输入

        Returns:
            格式化后的结果
        """
        results = inputs.get("results", [])

        if not results:
            return {"formatted_results": "未找到相关文档。"}

        formatted_results = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0)
            doc_id = result.get("id", f"文档{i}")

            # 格式化每个检索结果
            formatted_result = f"文档{i} (ID: {doc_id}, 相似度: {score:.3f}):\n{content}\n"
            formatted_results.append(formatted_result)

        formatted_text = "\n".join(formatted_results)
        return {"formatted_results": formatted_text}


class DocumentProcessorVertex(FunctionVertex):
    """文档处理顶点"""

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        vector_engine=None,
    ):
        super().__init__(
            id=id,
            name=name or "文档处理",
            task=self.process_documents,
            params=params or {},
            variables=variables or [],
        )
        self.chunk_size = params.get("chunk_size", 1000) if params else 1000
        self.chunk_overlap = params.get("chunk_overlap", 200) if params else 200
        self.vector_engine = vector_engine

    def _load_existing_hashes(self) -> Dict[str, Dict]:
        """
        加载已处理文件的哈希内容

        Returns:
            包含内容哈希和元数据的字典
        """
        if self.vector_engine and hasattr(self.vector_engine, "content_hashes"):
            return self.vector_engine.content_hashes
        return {}

    def _get_document_hashes(self, docs: List) -> Dict[str, Dict]:
        """
        获取当前要处理文档的哈希内容

        Args:
            docs: 文档列表

        Returns:
            文档路径/ID到哈希和内容的映射
        """
        doc_hashes = {}

        for i, doc in enumerate(docs):
            doc_key = None
            content = None
            metadata = {}

            if isinstance(doc, str):
                if os.path.exists(doc):
                    # 文件路径
                    doc_key = doc
                    content = self._load_file(doc)
                    if content and os.path.exists(doc):
                        metadata = {"source": doc, "mtime": os.path.getmtime(doc), "file_size": os.path.getsize(doc)}
                else:
                    # 文本内容
                    doc_key = f"text_{i}"
                    content = doc
                    metadata = {"source": "text", "mtime": 0}

            elif isinstance(doc, dict):
                content = doc.get("content", "")
                doc_key = doc.get("metadata", {}).get("source", f"dict_{i}")
                metadata = doc.get("metadata", {})

            if content and doc_key:
                source_path = metadata.get("source")
                file_path = source_path if source_path and source_path != "text" else None
                content_hash = self._generate_content_hash(content, file_path=file_path)
                doc_hashes[doc_key] = {
                    "hash": content_hash,
                    "content": content,
                    "metadata": metadata,
                    "original_index": i,
                }

        return doc_hashes

    def _filter_duplicates(self, doc_hashes: Dict[str, Dict], existing_hashes: Dict[str, Dict]) -> tuple:
        """
        过滤重复文档

        Args:
            doc_hashes: 当前文档哈希
            existing_hashes: 已存在的哈希

        Returns:
            (需要处理的文档, 跳过的文档列表)
        """
        to_process = {}
        skipped = []

        for doc_key, doc_info in doc_hashes.items():
            content_hash = doc_info["hash"]

            if content_hash in existing_hashes:
                # 内容重复，跳过
                skipped.append(doc_key)
            else:
                # 新内容，需要处理
                to_process[doc_key] = doc_info

        return to_process, skipped

    def _process_unique_documents(self, to_process: Dict[str, Dict]) -> List[Dict]:
        """
        处理非重复文档，进行分块

        Args:
            to_process: 需要处理的文档

        Returns:
            处理后的文档块列表
        """
        processed_docs = []

        for doc_key, doc_info in to_process.items():
            content = doc_info["content"]
            metadata = doc_info["metadata"]
            original_index = doc_info["original_index"]

            # 对文档进行分块
            chunks = self._chunk_text(content)

            for j, chunk in enumerate(chunks):
                processed_docs.append(
                    {
                        "id": f"doc_{original_index}_chunk_{j}",
                        "content": chunk,
                        "metadata": {
                            **metadata,
                            "chunk_index": j,
                            "total_chunks": len(chunks),
                            "length": len(chunk),
                        },
                    }
                )

        return processed_docs

    def _update_vector_hashes(self, doc_hashes: Dict[str, Dict]):
        """
        将新的文档哈希信息更新到向量引擎中

        Args:
            doc_hashes: 文档哈希信息
        """
        if self.vector_engine and hasattr(self.vector_engine, "content_hashes"):
            for doc_key, doc_info in doc_hashes.items():
                content_hash = doc_info["hash"]
                metadata = doc_info["metadata"]
                self.vector_engine.content_hashes[content_hash] = {
                    "id": f"doc_{doc_info['original_index']}",
                    "metadata": metadata,
                }

    def process_documents(self, inputs: Dict[str, Any], context=None):
        """
        处理文档，支持多种格式和分块，并在构建索引前检查重复

        Args:
            inputs: 包含文档路径或内容的输入

        Returns:
            处理后的文档列表
        """
        local_inputs = self.resolve_dependencies(inputs=inputs)
        docs = local_inputs.get("docs", [])

        if isinstance(docs, str):
            docs = [docs]

        # 1. 先加载以往处理过的文件的哈希内容
        existing_hashes = self._load_existing_hashes()

        # 2. 对这次要处理的文件获取哈希内容
        doc_hashes = self._get_document_hashes(docs)

        # 3. 如果有相同的，则跳过；如果不同，继续处理
        to_process, skipped = self._filter_duplicates(doc_hashes, existing_hashes)

        # 4. 处理非重复文档
        processed_docs = self._process_unique_documents(to_process)

        # 5. 更新向量引擎中的哈希信息，避免以后再重复处理
        self._update_vector_hashes(to_process)

        # 日志输出
        if len(skipped) > 0:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块，跳过 {len(skipped)} 个重复文档")
        else:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块")

        # 如果所有文档都被去重了，返回空列表表示跳过后续处理
        if not processed_docs:
            logging.info("所有文档都已存在，跳过embedding和向量存储步骤")
            return {"docs": []}

        return {"docs": processed_docs}

    def _load_file(self, file_path: str) -> Optional[str]:
        """加载文件内容，支持多种编码兜底"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in {".txt", ".md"}:
                # 尝试多种编码方式
                for encoding in ["utf-8", "gbk", "gb2312", "big5", "utf-16", "latin-1"]:
                    try:
                        with open(file_path, "r", encoding=encoding) as f:
                            content = f.read()
                            logging.info(f"成功使用 {encoding} 编码读取文件: {file_path}")
                            return content
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        break

                # 如果所有编码都失败，尝试二进制读取并强制解码
                try:
                    with open(file_path, "rb") as f:
                        raw_content = f.read()
                        content = raw_content.decode("utf-8", errors="ignore")
                        logging.warning(f"使用忽略错误的 UTF-8 解码读取文件: {file_path}")
                        return content
                except Exception:
                    logging.error(f"无法以任何编码方式读取文件: {file_path}")
                    return None

            elif file_ext == ".pdf":
                return self._load_pdf(file_path)

            elif file_ext in {".docx", ".doc"}:
                return self._load_word(file_path)

            else:
                logging.warning(f"不支持的文件格式: {file_ext}")
                return None

        except Exception as e:
            logging.error(f"加载文件 {file_path} 失败: {e}")
            return None

    def _load_pdf(self, file_path: str) -> Optional[str]:
        """加载PDF文件"""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                # 清理PDF文本，去除多余的空白字符
                text = self._clean_pdf_text(text)
                return text
        except ImportError:
            logging.error("请安装PyPDF2: pip install PyPDF2")
            return None
        except Exception as e:
            logging.error(f"PDF加载失败: {e}")
            return None

    def _clean_pdf_text(self, text: str) -> str:
        """清理PDF文本，去除多余的空白字符和换行符"""
        import re

        # 去除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        # 去除行首行尾空白
        text = text.strip()
        # 将多个换行符替换为单个换行符
        text = re.sub(r"\n+", "\n", text)

        return text

    def _load_word(self, file_path: str) -> Optional[str]:
        """加载Word文件"""
        try:
            from docx import Document

            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            logging.error("请安装python-docx: pip install python-docx")
            return None
        except Exception as e:
            logging.error(f"Word文档加载失败: {e}")
            return None

    def _chunk_text(self, text: str) -> List[str]:
        """
        将文本分块

        Args:
            text: 输入文本

        Returns:
            分块后的文本列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 寻找最近的句子结束符
                sentence_end = max(
                    text.rfind(".", start, end),
                    text.rfind("!", start, end),
                    text.rfind("?", start, end),
                    text.rfind("\n", start, end),
                )

                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 计算下一个块的起始位置，考虑重叠
            start = max(start + 1, end - self.chunk_overlap)

        return chunks

    def _generate_content_hash(self, content: str, file_path: Optional[str] = None) -> str:
        """生成文档内容的哈希值，pdf/doc/docx用二进制hash，其它用文本hash"""
        import hashlib
        import os
        from pathlib import Path

        # 如果是PDF或Word等二进制文件，直接用文件二进制内容hash
        if file_path and Path(file_path).suffix.lower() in {".pdf", ".docx", ".doc"} and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            return hashlib.md5(file_bytes).hexdigest()
        # 否则用文本内容hash
        cleaned_content = self._clean_pdf_text(content).lower()
        return hashlib.md5(cleaned_content.encode("utf-8")).hexdigest()

    def _is_duplicate_content(self, content_hash: str) -> bool:
        """检查文档内容是否已存在（需要从向量引擎获取）"""
        # 这里需要从向量引擎获取内容哈希信息
        # 由于DocumentProcessorVertex无法直接访问向量引擎，我们暂时返回False
        # 实际的去重逻辑在VectorStoreVertex中处理
        return False

    def _get_existing_metadata(self, content_hash: str) -> Optional[Dict]:
        """获取已存在文档的元数据（需要从向量引擎获取）"""
        # 这里需要从向量引擎获取元数据信息
        # 由于DocumentProcessorVertex无法直接访问向量引擎，我们暂时返回None
        # 实际的元数据获取逻辑在VectorStoreVertex中处理
        return None


class UnifiedRAGWorkflowBuilder:
    """统一配置的RAG工作流构建器"""

    def __init__(self):
        """
        初始化统一配置的RAG工作流构建器
        """
        # 使用正确的配置文件路径
        # config_path = os.path.join(os.getcwd(), "config", "llm.yml")
        # 复用VertexFlowService的配置
        self.service = VertexFlowService()
        self.config = self.service._config
        self.embedding_provider = None
        self.vector_engine = None
        self.llm_model = None
        self._initialize_components()

    def _format_search_results(self, results):
        """格式化搜索结果，提取有用的信息"""
        if not results:
            return "未找到相关文档。"

        formatted_results = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0)
            doc_id = result.get("id", f"文档{i}")

            # 格式化每个检索结果
            formatted_result = f"文档{i} (ID: {doc_id}, 相似度: {score:.3f}):\n{content}\n"
            formatted_results.append(formatted_result)

        return "\n".join(formatted_results)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "embedding": {
                "local": {"enabled": True, "model_name": "all-MiniLM-L6-v2", "dimension": 384},
                "dashscope": {"enabled": False},
                "bce": {"enabled": False},
            },
            "vector": {
                "local": {"enabled": True, "dimension": 384, "index_name": "default"},
                "dashvector": {"enabled": False},
            },
            "llm": {"deepseek": {"enabled": True}},
            "document": {"chunk_size": 1000, "chunk_overlap": 200},
            "retrieval": {"top_k": 3, "similarity_threshold": 0.3, "rerank": False},
        }

    def _initialize_components(self):
        """初始化组件"""
        # 初始化嵌入提供者
        if isinstance(self.config, dict):
            embedding_config = self.config.get("embedding", {})
        else:
            embedding_config = {}

        # 优先使用启用的嵌入提供者
        if embedding_config.get("dashscope", {}).get("enabled", False):
            try:
                self.embedding_provider = self.service.get_embedding(EmbeddingType.DASHSCOPE)
                logging.info("使用DashScope嵌入提供者")
            except Exception as e:
                logging.warning(f"无法创建DashScope嵌入提供者: {e}")
                self._fallback_to_local_embedding()
        elif embedding_config.get("bce", {}).get("enabled", False):
            try:
                self.embedding_provider = self.service.get_embedding(EmbeddingType.BCE)
                logging.info("使用BCE嵌入提供者")
            except Exception as e:
                logging.warning(f"无法创建BCE嵌入提供者: {e}")
                self._fallback_to_local_embedding()
        elif embedding_config.get("local", {}).get("enabled", True):
            # 使用本地嵌入
            local_config = embedding_config.get("local", {})
            model_name = local_config.get("model_name", "all-MiniLM-L6-v2")
            use_mirror = local_config.get("use_mirror", True)
            mirror_url = local_config.get("mirror_url", "https://hf-mirror.com")

            self.embedding_provider = LocalEmbeddingProvider(
                model_name=model_name, use_mirror=use_mirror, mirror_url=mirror_url
            )
            logging.info("使用本地嵌入提供者")
        else:
            # 没有配置任何嵌入提供者，使用本地嵌入作为默认
            self._fallback_to_local_embedding()

        # 初始化向量引擎
        vector_config = self.config.get("vector", {})

        # 优先使用启用的向量引擎
        if vector_config.get("dashvector", {}).get("enabled", False):
            try:
                self.vector_engine = self.service.get_vector_engine()
                logging.info("使用DashVector引擎")
            except Exception as e:
                logging.warning(f"无法创建DashVector引擎: {e}")
                self._fallback_to_local_vector_engine()
        elif vector_config.get("local", {}).get("enabled", True):
            # 使用本地向量引擎
            local_config = vector_config.get("local", {})
            persist_dir = local_config.get("persist_dir", None)

            self.vector_engine = LocalVectorEngine(
                dimension=local_config.get("dimension", 384),
                index_name=local_config.get("index_name", "default"),
                persist_dir=persist_dir,
            )
            logging.info("使用本地向量引擎")
        else:
            # 没有配置任何向量引擎，使用本地向量引擎作为默认
            self._fallback_to_local_vector_engine()

        # 初始化LLM模型
        try:
            # 直接使用service的get_chatmodel方法，它会自动处理配置和选择启用的模型
            self.llm_model = self.service.get_chatmodel()
            logging.info(f"llm config : {self.config['llm']}")
            logging.info(
                f"使用LLM模型: {self.llm_model.model_name() if hasattr(self.llm_model, 'model_name') else 'default'}"
            )
        except Exception as e:
            logging.error(f"无法创建LLM模型: {e}")
            raise ValueError("无法初始化LLM模型，请检查配置")

    def _fallback_to_local_embedding(self):
        """回退到本地嵌入提供者"""
        # 使用默认配置回退
        self.embedding_provider = LocalEmbeddingProvider(
            model_name="all-MiniLM-L6-v2", use_mirror=True, mirror_url="https://hf-mirror.com"
        )
        logging.info("回退到本地嵌入提供者")

    def _fallback_to_local_vector_engine(self):
        """回退到本地向量引擎"""
        self.vector_engine = LocalVectorEngine()
        logging.info("回退到本地向量引擎")

    def build_smart_indexing_workflow(self) -> Workflow:
        """构建智能索引工作流，在构建索引前先检查重复"""
        document_config = self.config.get("document", {})

        # 创建工作流上下文
        context = WorkflowContext()

        # 创建顶点
        source_vertex = SourceVertex(id="SOURCE", name="文档输入", task=lambda inputs, context: inputs)

        # 智能文档处理器，在构建索引前检查重复
        smart_doc_processor = DocumentProcessorVertex(
            id="SMART_DOC_PROCESSOR",
            name="智能文档处理",
            params=document_config if isinstance(document_config, dict) else {},
            variables=[
                {
                    "source_scope": "SOURCE",
                    "source_var": "docs",
                    "local_var": "docs",
                }
            ],
            vector_engine=self.vector_engine,
        )

        embedding_vertex = EmbeddingVertex(
            id="EMBEDDING",
            name="文档向量化",
            embedding_provider=self.embedding_provider,
            variables=(
                [
                    {
                        "source_scope": "SMART_DOC_PROCESSOR",
                        "source_var": "docs",
                        "local_var": "docs",
                    }
                ]
                if self.embedding_provider
                else None
            ),
        )

        vector_store = VectorStoreVertex(
            id="VECTOR_STORE",
            name="向量存储",
            vector_engine=self.vector_engine,
            variables=[
                {
                    "source_scope": "EMBEDDING",
                    "source_var": "embeddings",
                    "local_var": "docs",
                }
            ],
        )

        sink_vertex = SinkVertex(id="SINK", name="完成", task=lambda inputs, context: logging.info("智能索引构建完成"))

        # 创建工作流
        workflow = Workflow(context=context)
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(smart_doc_processor)
        workflow.add_vertex(embedding_vertex)
        workflow.add_vertex(vector_store)
        workflow.add_vertex(sink_vertex)

        # 构建工作流图
        source_vertex | smart_doc_processor | embedding_vertex | vector_store | sink_vertex

        return workflow

    def _smart_process_documents(self, inputs: Dict[str, Any], context=None):
        """
        智能文档处理，只根据内容hash去重，hash已存在则跳过embedding
        """
        docs = inputs.get("docs", [])
        if isinstance(docs, str):
            docs = [docs]
        processed_docs = []
        skipped_docs = []
        content_hashes = {}
        if hasattr(self.vector_engine, "content_hashes"):
            content_hashes = self.vector_engine.content_hashes

        # 记录开始处理
        logging.info(f"开始智能处理 {len(docs)} 个文档")

        for i, doc in enumerate(docs):
            if isinstance(doc, str):
                if os.path.exists(doc):
                    content = self._load_file_content(doc)
                    if content:
                        content_hash = self._generate_content_hash(content, file_path=doc)
                        if content_hash in content_hashes:
                            skipped_docs.append(doc)
                            continue
                        processed_docs.extend(self._process_single_document(doc, content, i))
                else:
                    content = doc
                    if content:
                        content_hash = self._generate_content_hash(content)
                        if content_hash in content_hashes:
                            skipped_docs.append(f"text_{i}")
                            continue
                        processed_docs.extend(self._process_single_document(f"text_{i}", content, i))
            elif isinstance(doc, dict):
                content = doc.get("content", "")
                file_path = doc.get("metadata", {}).get("source", None)
                if content:
                    content_hash = self._generate_content_hash(content, file_path=file_path)
                    if content_hash in content_hashes:
                        skipped_docs.append(doc.get("metadata", {}).get("source", f"dict_{i}"))
                        continue
                    processed_docs.append(doc)
                else:
                    processed_docs.append(doc)

        # 简化日志输出，只显示关键统计信息
        if len(skipped_docs) > 0:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块，跳过 {len(skipped_docs)} 个重复文档")
        else:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块")

        return {"docs": processed_docs}

    def _process_single_document(self, doc_path: str, content: str, doc_index: int, force_update: bool = False):
        """处理单个文档，返回文档块列表"""
        chunks = self._chunk_text(content)
        processed_chunks = []

        for j, chunk in enumerate(chunks):
            metadata = {
                "source": doc_path,
                "chunk_index": j,
                "total_chunks": len(chunks),
                "length": len(chunk),
            }

            if os.path.exists(doc_path):
                metadata["mtime"] = os.path.getmtime(doc_path)
                metadata["file_size"] = os.path.getsize(doc_path)

            if force_update:
                metadata["force_update"] = True

            processed_chunks.append(
                {
                    "id": f"doc_{doc_index}_chunk_{j}",
                    "content": chunk,
                    "metadata": metadata,
                }
            )

        return processed_chunks

    def _load_file_content(self, file_path: str) -> Optional[str]:
        """加载文件内容，支持多种编码兜底"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in {".txt", ".md"}:
                # 尝试多种编码方式
                for encoding in ["utf-8", "gbk", "gb2312", "big5", "utf-16", "latin-1"]:
                    try:
                        with open(file_path, "r", encoding=encoding) as f:
                            content = f.read()
                            logging.info(f"成功使用 {encoding} 编码读取文件: {file_path}")
                            return content
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        break

                # 如果所有编码都失败，尝试二进制读取并强制解码
                try:
                    with open(file_path, "rb") as f:
                        raw_content = f.read()
                        content = raw_content.decode("utf-8", errors="ignore")
                        logging.warning(f"使用忽略错误的 UTF-8 解码读取文件: {file_path}")
                        return content
                except Exception:
                    logging.error(f"无法以任何编码方式读取文件: {file_path}")
                    return None
            elif file_ext == ".pdf":
                return self._load_pdf_content(file_path)
            elif file_ext in {".docx", ".doc"}:
                return self._load_word_content(file_path)
            else:
                logging.warning(f"不支持的文件格式: {file_ext}")
                return None
        except Exception as e:
            logging.error(f"加载文件 {file_path} 失败: {e}")
            return None

    def _load_pdf_content(self, file_path: str) -> Optional[str]:
        """加载PDF文件内容"""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                # 清理PDF文本，去除多余的空白字符
                text = self._clean_pdf_text(text)
                return text
        except ImportError:
            logging.error("请安装PyPDF2: pip install PyPDF2")
            return None
        except Exception as e:
            logging.error(f"PDF加载失败: {e}")
            return None

    def _clean_pdf_text(self, text: str) -> str:
        """清理PDF文本，去除多余的空白字符和换行符"""
        import re

        # 去除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        # 去除行首行尾空白
        text = text.strip()
        # 将多个换行符替换为单个换行符
        text = re.sub(r"\n+", "\n", text)

        return text

    def _load_word_content(self, file_path: str) -> Optional[str]:
        """加载Word文件内容"""
        try:
            from docx import Document

            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            logging.error("请安装python-docx: pip install python-docx")
            return None
        except Exception as e:
            logging.error(f"Word文档加载失败: {e}")
            return None

    def _chunk_text(self, text: str) -> List[str]:
        """将文本分块"""
        chunk_size = 1000
        chunk_overlap = 200

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                sentence_end = max(
                    text.rfind(".", start, end),
                    text.rfind("!", start, end),
                    text.rfind("?", start, end),
                    text.rfind("\n", start, end),
                )

                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = max(start + 1, end - chunk_overlap)

        return chunks

    def _generate_content_hash(self, content: str, file_path: Optional[str] = None) -> str:
        """生成文档内容的哈希值，pdf/doc/docx用二进制hash，其它用文本hash"""
        import hashlib
        import os
        from pathlib import Path

        # 如果是PDF或Word等二进制文件，直接用文件二进制内容hash
        if file_path and Path(file_path).suffix.lower() in {".pdf", ".docx", ".doc"} and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            return hashlib.md5(file_bytes).hexdigest()
        # 否则用文本内容hash
        cleaned_content = self._clean_pdf_text(content).lower()
        return hashlib.md5(cleaned_content.encode("utf-8")).hexdigest()

    def build_indexing_workflow(self) -> Workflow:
        """构建索引工作流"""
        document_config = self.config.get("document", {})

        # 创建工作流上下文
        context = WorkflowContext()

        # 创建顶点
        source_vertex = SourceVertex(id="SOURCE", name="文档输入", task=lambda inputs, context: inputs)

        doc_processor = DocumentProcessorVertex(
            id="DOC_PROCESSOR",
            name="文档处理",
            params=document_config if isinstance(document_config, dict) else {},
            variables=[
                {
                    "source_scope": "SOURCE",
                    "source_var": "docs",
                    "local_var": "docs",
                }
            ],
            vector_engine=self.vector_engine,
        )

        embedding_vertex = EmbeddingVertex(
            id="EMBEDDING",
            name="文档向量化",
            embedding_provider=self.embedding_provider,
            variables=[
                {
                    "source_scope": "DOC_PROCESSOR",
                    "source_var": "docs",
                    "local_var": "docs",
                }
            ],
        )

        vector_store = VectorStoreVertex(
            id="VECTOR_STORE",
            name="向量存储",
            vector_engine=self.vector_engine,
            variables=[
                {
                    "source_scope": "EMBEDDING",
                    "source_var": "embeddings",
                    "local_var": "docs",
                }
            ],
        )

        sink_vertex = SinkVertex(id="SINK", name="完成", task=lambda inputs, context: logging.info("索引构建完成"))

        # 创建工作流
        workflow = Workflow(context=context)
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(doc_processor)
        workflow.add_vertex(embedding_vertex)
        workflow.add_vertex(vector_store)
        workflow.add_vertex(sink_vertex)

        # 构建工作流图
        source_vertex | doc_processor | embedding_vertex | vector_store | sink_vertex

        return workflow

    def build_query_workflow(self) -> Workflow:
        """构建查询工作流"""
        retrieval_config = self.config.get("retrieval", {})
        prompts = self.config.get("prompts", {})

        # 创建工作流上下文
        context = WorkflowContext()

        # 创建顶点
        source_vertex = SourceVertex(id="QUERY_SOURCE", name="查询输入", task=lambda inputs, context: inputs)

        query_embedding = EmbeddingVertex(
            id="QUERY_EMBEDDING",
            name="查询向量化",
            embedding_provider=self.embedding_provider,
            variables=[
                {
                    "source_scope": "QUERY_SOURCE",
                    "source_var": "query",
                    "local_var": "text",
                }
            ],
        )

        vector_query = VectorQueryVertex(
            id="VECTOR_QUERY",
            name="向量检索",
            vector_engine=self.vector_engine,
            params={
                "top_k": retrieval_config.get("top_k", 3),
                "similarity_threshold": retrieval_config.get("similarity_threshold", 0.3),
            },
            variables=[
                {
                    "source_scope": "QUERY_EMBEDDING",
                    "source_var": "embeddings",
                    "local_var": "query",
                }
            ],
        )

        result_formatter = ResultFormatterVertex(
            id="RESULT_FORMATTER",
            name="结果格式化",
            params={},
            variables=[
                {
                    "source_scope": "VECTOR_QUERY",
                    "source_var": "results",
                    "local_var": "results",
                }
            ],
        )

        llm_vertex = LLMVertex(
            id="LLM",
            name="生成回答",
            model=self.llm_model,
            params={
                SYSTEM: prompts.get("system", "你是一个有用的AI助手。"),
                USER: [
                    "基于以下上下文信息回答问题：\n\n上下文：{{formatted_results}}\n\n问题：{{user_question}}\n\n请提供准确、有用的回答。"
                ],
            },
            variables=[
                {
                    "source_scope": "RESULT_FORMATTER",
                    "source_var": "formatted_results",
                    "local_var": "formatted_results",
                },
                {
                    "source_scope": "QUERY_SOURCE",
                    "source_var": "query",
                    "local_var": "user_question",
                },
            ],
        )

        sink_vertex = SinkVertex(
            id="ANSWER_SINK",
            name="输出答案",
            task=lambda inputs, context: logging.info(f"生成答案: {inputs.get('LLM', '')}"),
        )

        # 创建工作流
        workflow = Workflow(context=context)
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(query_embedding)
        workflow.add_vertex(vector_query)
        workflow.add_vertex(result_formatter)
        workflow.add_vertex(llm_vertex)
        workflow.add_vertex(sink_vertex)

        # 构建工作流图
        source_vertex | query_embedding | vector_query | result_formatter | llm_vertex | sink_vertex

        return workflow


class UnifiedRAGSystem:
    """统一配置的RAG系统"""

    def __init__(self):
        """
        初始化统一配置的RAG系统

        """
        self.builder = UnifiedRAGWorkflowBuilder()

        self.indexing_workflow = None
        self.query_workflow = None

        # 性能优化: 添加缓存和复用机制
        self._query_workflow_instance = None
        self._embedding_cache = {}  # 查询embedding缓存
        self._is_initialized = False
        self._indexing_only_mode = False  # 仅索引模式标志

    def _lazy_initialize(self, indexing_only: bool = False):
        """
        延迟初始化，只在需要时构建工作流

        Args:
            indexing_only: 是否仅需要索引功能（不初始化LLM）
        """
        if not self._is_initialized:
            self._indexing_only_mode = indexing_only
            if indexing_only:
                # 仅构建索引工作流，不初始化LLM
                self.indexing_workflow = self.builder.build_smart_indexing_workflow()
                logging.info("仅索引模式：跳过LLM初始化")
            else:
                # 完整初始化
                self.build_workflows()
            self._is_initialized = True

    def build_workflows(self):
        """构建索引和查询工作流"""
        self.indexing_workflow = self.builder.build_smart_indexing_workflow()

        # 只有在非仅索引模式下才构建查询工作流
        if not self._indexing_only_mode:
            try:
                self.query_workflow = self.builder.build_query_workflow()
                # 性能优化: 预构建可复用的查询工作流实例
                self._query_workflow_instance = self.builder.build_query_workflow()
                logging.info("统一配置RAG工作流构建完成")
            except Exception as e:
                logging.warning(f"查询工作流构建失败，可能是LLM配置问题: {e}")
                logging.info("系统将以仅索引模式运行")
                self._indexing_only_mode = True

    def get_vector_db_stats(self):
        """获取向量数据库统计信息"""
        if hasattr(self.builder, "vector_engine") and self.builder.vector_engine:
            if hasattr(self.builder.vector_engine, "get_stats"):
                return self.builder.vector_engine.get_stats()
            else:
                return {"message": "向量引擎不支持统计信息"}
        return {"message": "向量引擎未初始化"}

    def _get_cached_embedding(self, text: str):
        """获取缓存的查询embedding"""
        import hashlib

        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        return self._embedding_cache.get(text_hash)

    def _cache_embedding(self, text: str, embedding):
        """缓存查询embedding"""
        import hashlib

        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        self._embedding_cache[text_hash] = embedding

        # 限制缓存大小，避免内存溢出
        if len(self._embedding_cache) > 100:
            # 删除最旧的缓存项
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]

    def index_documents(self, documents: List[str], force_reindex: bool = False, update_existing: bool = True):
        """
        索引文档

        Args:
            documents: 文档列表，可以是文件路径或文档内容
            force_reindex: 是否强制重新索引，默认False
            update_existing: 是否更新已存在的文档，默认True
        """
        # 仅索引模式初始化，不加载LLM
        self._lazy_initialize(indexing_only=True)

        # 检查向量数据库状态
        stats = self.get_vector_db_stats()
        existing_docs = stats.get("total_documents", 0)

        if isinstance(existing_docs, (int, float)) and existing_docs > 0 and not force_reindex and not update_existing:
            print(
                f"向量数据库中已有 {existing_docs} 个文档，跳过索引。使用 force_reindex=True 强制重新索引，或 update_existing=True 更新现有文档。"
            )
            return

        if isinstance(existing_docs, (int, float)) and existing_docs > 0 and update_existing:
            print(f"向量数据库中已有 {existing_docs} 个文档，将检测并更新变化的文档...")
        else:
            logging.info(f"开始索引 {len(documents)} 个文档")

        # 每次执行都创建新的工作流实例，避免重复运行错误
        workflow_instance = self.builder.build_smart_indexing_workflow()
        workflow_instance.execute_workflow(source_inputs={"docs": documents})

        # 显示索引后的统计信息
        new_stats = self.get_vector_db_stats()
        new_doc_count = new_stats.get("total_documents", 0)
        logging.info(f"文档索引完成，向量数据库现在包含 {new_doc_count} 个文档")

        if update_existing and isinstance(existing_docs, (int, float)) and existing_docs > 0:
            if isinstance(new_doc_count, (int, float)):
                added_docs = new_doc_count - existing_docs
                if added_docs > 0:
                    print(f"更新完成：新增了 {added_docs} 个文档")
                else:
                    print("更新完成：没有新增文档（可能都是重复内容）")

    def query(self, question: str, use_cache: bool = True) -> str:
        """
        查询问题（性能优化版本）

        Args:
            question: 问题
            use_cache: 是否使用embedding缓存，默认True

        Returns:
            生成的答案
        """
        # 查询需要完整初始化（包括LLM）
        self._lazy_initialize(indexing_only=False)

        # 检查是否在仅索引模式
        if self._indexing_only_mode:
            logging.warning("系统在仅索引模式下运行，无法执行LLM查询，回退到快速查询模式")
            return self.query_fast(question)

        logging.info(f"查询问题: {question}")

        # 性能优化: 复用工作流实例，避免重复构建
        if self._query_workflow_instance is None:
            try:
                self._query_workflow_instance = self.builder.build_query_workflow()
            except Exception as e:
                logging.error(f"查询工作流构建失败: {e}")
                return self.query_fast(question)

        try:
            # 清理之前的输出状态
            self._reset_workflow_state(self._query_workflow_instance)

            retrieval_config = self.builder.config.get("retrieval", {}) if isinstance(self.builder.config, dict) else {}

            self._query_workflow_instance.execute_workflow(
                source_inputs={
                    "query": question,
                    "top_k": retrieval_config.get("top_k", 3) if isinstance(retrieval_config, dict) else 3,
                    "similarity_threshold": (
                        retrieval_config.get("similarity_threshold", 0.3) if isinstance(retrieval_config, dict) else 0.3
                    ),
                }
            )

            # 获取LLM的输出
            llm_vertex = self._query_workflow_instance.get_vertice_by_id("LLM")
            if llm_vertex and hasattr(llm_vertex, "output"):
                return llm_vertex.output if llm_vertex.output else "无法生成答案"
            else:
                return "无法生成答案"

        except Exception as e:
            logging.error(f"查询执行失败: {e}")
            # 如果复用的工作流失败，尝试创建新的
            try:
                workflow_instance = self.builder.build_query_workflow()
                retrieval_config = (
                    self.builder.config.get("retrieval", {}) if isinstance(self.builder.config, dict) else {}
                )

                workflow_instance.execute_workflow(
                    source_inputs={
                        "query": question,
                        "top_k": retrieval_config.get("top_k", 3) if isinstance(retrieval_config, dict) else 3,
                        "similarity_threshold": (
                            retrieval_config.get("similarity_threshold", 0.3)
                            if isinstance(retrieval_config, dict)
                            else 0.3
                        ),
                    }
                )

                llm_vertex = workflow_instance.get_vertice_by_id("LLM")
                if llm_vertex and hasattr(llm_vertex, "output"):
                    return llm_vertex.output if llm_vertex.output else "无法生成答案"
                else:
                    return "无法生成答案"
            except Exception as e2:
                logging.error(f"查询彻底失败，回退到快速查询: {e2}")
                return self.query_fast(question)

    def _reset_workflow_state(self, workflow_instance):
        """重置工作流状态，准备下次执行"""
        if workflow_instance and hasattr(workflow_instance, "vertices"):
            for vertex in workflow_instance.vertices.values():
                if hasattr(vertex, "output"):
                    vertex.output = None
                if hasattr(vertex, "_executed"):
                    vertex._executed = False

    def query_fast(self, question: str) -> str:
        """
        快速查询模式（最小化LLM调用）

        Args:
            question: 问题

        Returns:
            格式化的检索结果或LLM答案
        """
        # 快速查询只需要索引组件，不需要LLM
        self._lazy_initialize(indexing_only=True)

        # 直接进行向量检索，跳过LLM生成
        try:
            # 获取查询embedding
            if self.builder.embedding_provider:
                query_embedding = self.builder.embedding_provider.embedding(question)
                if query_embedding:
                    # 直接搜索向量数据库
                    retrieval_config = (
                        self.builder.config.get("retrieval", {}) if isinstance(self.builder.config, dict) else {}
                    )
                    top_k = retrieval_config.get("top_k", 3) if isinstance(retrieval_config, dict) else 3

                    results = self.builder.vector_engine.search(query_embedding, top_k=top_k, include_vector=False)

                    # 格式化结果
                    if results:
                        formatted_results = []
                        for i, result in enumerate(results, 1):
                            content = result.get("content", "")
                            score = result.get("score", 0)
                            doc_id = result.get("id", f"文档{i}")
                            formatted_result = f"文档{i} (ID: {doc_id}, 相似度: {score:.3f}):\n{content}\n"
                            formatted_results.append(formatted_result)
                        return "\n".join(formatted_results)
                    else:
                        return "未找到相关文档"
                else:
                    return "查询embedding生成失败"
            else:
                return "embedding提供者未初始化"
        except Exception as e:
            logging.error(f"快速查询失败: {e}")
            return f"查询失败: {e}"

    def start_interactive_mode(self, fast_mode: bool = False):
        """
        启动交互式查询模式（性能优化版本）

        Args:
            fast_mode: 是否使用快速模式（跳过LLM生成）
        """
        # 根据模式选择初始化方式
        self._lazy_initialize(indexing_only=fast_mode)

        print("\n=== 交互式查询模式 ===")
        if fast_mode:
            print("(快速模式 - 仅显示检索结果，不调用LLM)")
        else:
            if self._indexing_only_mode:
                print("(检测到LLM配置问题，自动切换到快速模式)")
                fast_mode = True
        print("输入 'quit', 'exit' 或 '退出' 来结束")
        print("输入 'stats' 查看数据库统计")
        print("输入 'cache' 查看缓存状态")
        print("=" * 50)

        query_count = 0
        start_time = time.time()

        while True:
            try:
                question = input("\n请输入您的问题: ").strip()

                if question.lower() in ["quit", "exit", "退出"]:
                    break
                elif question.lower() == "stats":
                    stats = self.get_vector_db_stats()
                    print(f"\n数据库统计: {stats}")
                    continue
                elif question.lower() == "cache":
                    print(f"\n缓存状态: {len(self._embedding_cache)} 个查询已缓存")
                    continue

                if not question:
                    continue

                query_start = time.time()
                print("\n正在生成答案...")

                if fast_mode or self._indexing_only_mode:
                    answer = self.query_fast(question)
                else:
                    answer = self.query(question)

                query_time = time.time() - query_start
                query_count += 1

                print(f"\n答案: {answer}")
                print(f"查询耗时: {query_time:.2f}秒")
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n\n已取消查询")
                break
            except EOFError:
                break

        total_time = time.time() - start_time
        if query_count > 0:
            avg_time = total_time / query_count
            print(f"\n会话统计: {query_count} 次查询，平均耗时 {avg_time:.2f}秒")

    def show_workflows(self):
        """显示工作流图"""
        if self.indexing_workflow:
            print("=== 索引工作流 ===")
            self.indexing_workflow.show_graph()

        if self.query_workflow:
            print("\n=== 查询工作流 ===")
            self.query_workflow.show_graph()
        elif self._indexing_only_mode:
            print("\n=== 查询工作流 ===")
            print("(仅索引模式 - 查询工作流未构建)")


def main():
    """示例用法"""
    # 创建示例文档
    sample_docs = [
        "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
        "机器学习是人工智能的一个子集，它使计算机能够在没有明确编程的情况下学习和改进。",
        "深度学习是机器学习的一个分支，使用神经网络来模拟人脑的学习过程。",
        "自然语言处理是人工智能的一个领域，专注于计算机理解和生成人类语言的能力。",
        "计算机视觉是人工智能的一个分支，使计算机能够从图像和视频中理解和提取信息。",
    ]

    # 创建统一配置的RAG系统
    rag_system = UnifiedRAGSystem()

    # 构建工作流
    rag_system.build_workflows()

    # 显示工作流图
    rag_system.show_workflows()

    # 索引文档
    rag_system.index_documents(sample_docs)

    # 查询示例
    questions = ["什么是人工智能？", "机器学习和深度学习有什么区别？", "自然语言处理有什么应用？"]

    for question in questions:
        print(f"\n问题: {question}")
        answer = rag_system.query(question)
        print(f"答案: {answer}")


if __name__ == "__main__":
    main()
