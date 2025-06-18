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

    def __init__(self, id: str, name: str = None, params: Dict[str, Any] = None, variables=None):
        super().__init__(
            id=id,
            name=name,
            task=self.format_results,
            params=params,
            variables=variables,
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

    def __init__(self, id: str, name: str = None, params: Dict[str, Any] = None, variables=None):
        super().__init__(
            id=id,
            name=name,
            task=self.process_documents,
            params=params,
            variables=variables,
        )
        self.chunk_size = params.get("chunk_size", 1000) if params else 1000
        self.chunk_overlap = params.get("chunk_overlap", 200) if params else 200

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
            # 如果是字符串，当作单个文档处理
            docs = [docs]

        processed_docs = []
        skipped_docs = []

        for i, doc in enumerate(docs):
            if isinstance(doc, str):
                # 如果是文件路径，读取文件内容
                if os.path.exists(doc):
                    content = self._load_file(doc)
                    if content:
                        # 获取文件修改时间
                        file_mtime = os.path.getmtime(doc)

                        # 检查是否重复（基于内容哈希）
                        content_hash = self._generate_content_hash(content)
                        if self._is_duplicate_content(content_hash):
                            # 检查文件路径是否发生变化
                            existing_metadata = self._get_existing_metadata(content_hash)
                            if existing_metadata:
                                existing_path = existing_metadata.get("source", "")
                                if existing_path != doc:
                                    # 文件名发生变化，需要更新
                                    logging.info(f"文件名发生变化，需要更新: {existing_path} -> {doc}")
                                    # 对文档进行分块
                                    chunks = self._chunk_text(content)
                                    for j, chunk in enumerate(chunks):
                                        processed_docs.append(
                                            {
                                                "id": f"doc_{i}_chunk_{j}",
                                                "content": chunk,
                                                "metadata": {
                                                    "source": doc,
                                                    "chunk_index": j,
                                                    "total_chunks": len(chunks),
                                                    "length": len(chunk),
                                                    "mtime": file_mtime,
                                                    "file_size": os.path.getsize(doc) if os.path.exists(doc) else 0,
                                                    "force_update": True,  # 标记为强制更新
                                                },
                                            }
                                        )
                                else:
                                    # 相同路径，检查文件修改时间
                                    existing_mtime = existing_metadata.get("mtime", 0)
                                    if abs(file_mtime - existing_mtime) < 1:  # 1秒内的差异认为是相同
                                        skipped_docs.append(doc)
                                        continue
                                    else:
                                        # 文件内容已更新，需要重新索引
                                        logging.info(f"文件内容已更新，需要重新索引: {doc}")
                                        chunks = self._chunk_text(content)
                                        for j, chunk in enumerate(chunks):
                                            processed_docs.append(
                                                {
                                                    "id": f"doc_{i}_chunk_{j}",
                                                    "content": chunk,
                                                    "metadata": {
                                                        "source": doc,
                                                        "chunk_index": j,
                                                        "total_chunks": len(chunks),
                                                        "length": len(chunk),
                                                        "mtime": file_mtime,
                                                        "file_size": os.path.getsize(doc) if os.path.exists(doc) else 0,
                                                        "force_update": True,  # 标记为强制更新
                                                    },
                                                }
                                            )
                            else:
                                # 内容重复但元数据不存在，跳过
                                skipped_docs.append(doc)
                                continue
                        else:
                            # 新文档，进行分块
                            chunks = self._chunk_text(content)
                            for j, chunk in enumerate(chunks):
                                processed_docs.append(
                                    {
                                        "id": f"doc_{i}_chunk_{j}",
                                        "content": chunk,
                                        "metadata": {
                                            "source": doc,
                                            "chunk_index": j,
                                            "total_chunks": len(chunks),
                                            "length": len(chunk),
                                            "mtime": file_mtime,
                                            "file_size": os.path.getsize(doc) if os.path.exists(doc) else 0,
                                        },
                                    }
                                )
                else:
                    # 如果不是文件路径，当作文档内容
                    content = doc

                    if content:
                        # 检查是否重复
                        content_hash = self._generate_content_hash(content)
                        if self._is_duplicate_content(content_hash):
                            skipped_docs.append(f"text_{i}")
                            continue

                        # 对文档进行分块
                        chunks = self._chunk_text(content)
                        for j, chunk in enumerate(chunks):
                            processed_docs.append(
                                {
                                    "id": f"doc_{i}_chunk_{j}",
                                    "content": chunk,
                                    "metadata": {
                                        "source": "text",
                                        "chunk_index": j,
                                        "total_chunks": len(chunks),
                                        "length": len(chunk),
                                        "mtime": 0,  # 文本内容没有修改时间
                                    },
                                }
                            )
            elif isinstance(doc, dict):
                # 如果已经是字典格式，直接使用
                if "id" not in doc:
                    doc["id"] = f"doc_{i}"

                # 检查是否重复
                content = doc.get("content", "")
                if content:
                    content_hash = self._generate_content_hash(content)
                    if self._is_duplicate_content(content_hash):
                        # 检查是否需要更新
                        existing_metadata = self._get_existing_metadata(content_hash)
                        if existing_metadata:
                            existing_path = existing_metadata.get("source", "")
                            current_path = doc.get("metadata", {}).get("source", "")

                            if existing_path != current_path and current_path:
                                # 文件名发生变化，需要更新
                                logging.info(f"文件名发生变化，需要更新: {existing_path} -> {current_path}")
                                doc["force_update"] = True
                            else:
                                # 相同路径，跳过
                                skipped_docs.append(current_path or f"dict_{i}")
                                continue

                # 如果是文件路径，添加文件修改时间
                if "metadata" in doc and "source" in doc["metadata"]:
                    source_path = doc["metadata"]["source"]
                    if os.path.exists(source_path):
                        doc["metadata"]["mtime"] = os.path.getmtime(source_path)
                        doc["metadata"]["file_size"] = os.path.getsize(source_path)

                processed_docs.append(doc)

        # 简化日志输出，只显示关键统计信息
        if len(skipped_docs) > 0:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块，跳过 {len(skipped_docs)} 个重复文档")
        else:
            logging.info(f"文档处理完成: 生成 {len(processed_docs)} 个块")

        return {"docs": processed_docs}

    def _load_file(self, file_path: str) -> Optional[str]:
        """加载文件内容"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in {".txt", ".md"}:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

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

    def _generate_content_hash(self, content: str, file_path: str = None) -> str:
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
        embedding_config = self.config.get("embedding", {})

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
            self.embedding_provider = LocalEmbeddingProvider(local_config.get("model_name", "all-MiniLM-L6-v2"))
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
        self.embedding_provider = LocalEmbeddingProvider("all-MiniLM-L6-v2")
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
        smart_doc_processor = FunctionVertex(
            id="SMART_DOC_PROCESSOR",
            name="智能文档处理",
            task=self._smart_process_documents,
            params=document_config,
            variables=[
                {
                    "source_scope": "SOURCE",
                    "source_var": "docs",
                    "local_var": "docs",
                }
            ],
        )

        embedding_vertex = EmbeddingVertex(
            id="EMBEDDING",
            name="文档向量化",
            embedding_provider=self.embedding_provider,
            variables=[
                {
                    "source_scope": "SMART_DOC_PROCESSOR",
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
        """加载文件内容"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in {".txt", ".md"}:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
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

    def _generate_content_hash(self, content: str, file_path: str = None) -> str:
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
            params=document_config,
            variables=[
                {
                    "source_scope": "SOURCE",
                    "source_var": "docs",
                    "local_var": "docs",
                }
            ],
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

    def build_workflows(self):
        """构建索引和查询工作流"""
        self.indexing_workflow = self.builder.build_smart_indexing_workflow()
        self.query_workflow = self.builder.build_query_workflow()

        logging.info("统一配置RAG工作流构建完成")

    def get_vector_db_stats(self):
        """获取向量数据库统计信息"""
        if hasattr(self.builder, "vector_engine") and self.builder.vector_engine:
            if hasattr(self.builder.vector_engine, "get_stats"):
                return self.builder.vector_engine.get_stats()
            else:
                return {"message": "向量引擎不支持统计信息"}
        return {"message": "向量引擎未初始化"}

    def index_documents(self, documents: List[str], force_reindex: bool = False, update_existing: bool = True):
        """
        索引文档

        Args:
            documents: 文档列表，可以是文件路径或文档内容
            force_reindex: 是否强制重新索引，默认False
            update_existing: 是否更新已存在的文档，默认True
        """
        if not self.indexing_workflow:
            self.build_workflows()

        # 检查向量数据库状态
        stats = self.get_vector_db_stats()
        existing_docs = stats.get("total_documents", 0)

        if existing_docs > 0 and not force_reindex and not update_existing:
            print(
                f"向量数据库中已有 {existing_docs} 个文档，跳过索引。使用 force_reindex=True 强制重新索引，或 update_existing=True 更新现有文档。"
            )
            return

        if existing_docs > 0 and update_existing:
            print(f"向量数据库中已有 {existing_docs} 个文档，将检测并更新变化的文档...")
        else:
            logging.info(f"开始索引 {len(documents)} 个文档")

        # 每次执行都创建新的工作流实例，避免重复运行错误
        workflow_instance = self.builder.build_smart_indexing_workflow()
        workflow_instance.execute_workflow(source_inputs={"docs": documents})

        # 显示索引后的统计信息
        new_stats = self.get_vector_db_stats()
        logging.info(f"文档索引完成，向量数据库现在包含 {new_stats.get('total_documents', 0)} 个文档")

        if update_existing and existing_docs > 0:
            added_docs = new_stats.get("total_documents", 0) - existing_docs
            if added_docs > 0:
                print(f"更新完成：新增了 {added_docs} 个文档")
            else:
                print("更新完成：没有新增文档（可能都是重复内容）")

    def query(self, question: str) -> str:
        """
        查询问题

        Args:
            question: 问题

        Returns:
            生成的答案
        """
        if not self.query_workflow:
            self.build_workflows()

        retrieval_config = self.builder.config.get("retrieval", {})

        logging.info(f"查询问题: {question}")

        # 每次执行都创建新的工作流实例，避免重复运行错误
        workflow_instance = self.builder.build_query_workflow()
        workflow_instance.execute_workflow(
            source_inputs={
                "query": question,
                "top_k": retrieval_config.get("top_k", 3),
                "similarity_threshold": retrieval_config.get("similarity_threshold", 0.3),
            }
        )

        # 获取LLM的输出
        llm_output = workflow_instance.get_vertice_by_id("LLM").output
        return llm_output if llm_output else "无法生成答案"

    def show_workflows(self):
        """显示工作流图"""
        if self.indexing_workflow:
            print("=== 索引工作流 ===")
            self.indexing_workflow.show_graph()

        if self.query_workflow:
            print("\n=== 查询工作流 ===")
            self.query_workflow.show_graph()


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
