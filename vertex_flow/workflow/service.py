import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import yaml

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.rag_config import read_yaml_config_env_placeholder
from vertex_flow.workflow.utils import create_instance, default_config_path
from vertex_flow.workflow.vertex.vector_engines import DashVector

from .vertex.embedding_providers import BCEEmbedding, DashScopeEmbedding, TextEmbeddingProvider

logging = LoggerUtil.get_logger()

# MCP support
try:
    from vertex_flow.workflow.mcp_manager import get_mcp_manager

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP functionality not available")


class EmbeddingType(Enum):
    DASHSCOPE = "DashScopeEmbedding"
    BCE = "BCEEmbedding"


@dataclass
class VectorConfig:
    api_key: str
    endpoint: str
    cluster: str
    collection: str
    image_collection: str


class VertexFlowService:
    """
    VertexFlowService 单例类用于初始化和管理LLM（大型语言模型）的相关配置。
    它通过读取配置文件来加载模型的配置信息，并初始化一些关键的路径变量。
    """

    _instance = None
    _lock = None
    _config_cache = {}  # 添加配置缓存

    @staticmethod
    def _parse_bool(value) -> bool:
        """
        安全地解析布尔值，支持字符串和布尔类型

        Args:
            value: 要解析的值，可能是字符串或布尔类型

        Returns:
            bool: 解析后的布尔值
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            # 转换为小写并去除空格
            value_lower = value.lower().strip()
            # 真值
            if value_lower in ["true", "1", "yes", "on", "enabled"]:
                return True
            # 假值
            elif value_lower in ["false", "0", "no", "off", "disabled"]:
                return False
            else:
                # 无法解析的值，默认为False
                logging.warning(f"无法解析布尔值: '{value}'，默认为False")
                return False
        else:
            # 非字符串非布尔类型，尝试转换为布尔值
            try:
                return bool(value)
            except (ValueError, TypeError):
                logging.warning(f"无法转换值为布尔类型: {value}，默认为False")
                return False

    def __new__(cls, config_file=None):
        """单例模式实现"""
        if cls._instance is None:
            # 导入threading模块用于线程安全
            import threading

            if cls._lock is None:
                cls._lock = threading.Lock()

            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VertexFlowService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file=None):
        """
        初始化VertexFlowService实例。
        该方法主要负责读取配置文件，并初始化实例变量，供类的其他方法使用。
        """
        # 防止重复初始化
        if self._initialized:
            return

        # 如果没有指定配置文件，优先使用用户配置文件
        if config_file is None:
            import os
            from pathlib import Path

            # 检查用户配置文件是否存在
            user_config = Path.home() / ".vertex" / "config" / "llm.yml"
            if user_config.exists():
                config_file = str(user_config)
                logging.info(f"使用用户配置文件: {config_file}")
            else:
                config_file = default_config_path("llm.yml")
                logging.info(f"用户配置文件不存在，使用默认配置: {config_file}")

        # 读取并解析配置文件，初始化_config实例变量
        self._config = self._load_config(config_file)

        # 确保_config是字典类型
        if not isinstance(self._config, dict):
            raise ValueError(f"配置文件格式错误，期望字典类型，实际类型: {type(self._config)}")

        # 初始化工作流的根路径
        self.__workflow_root_path = self._config["workflow"]["dify"]["root-path"]

        # 标记为已初始化
        self._initialized = True

        # 不在这里初始化MCP，延迟到真正需要时
        # MCP初始化会在get_mcp_manager()中按需进行

    def _load_config(self, config_file):
        """加载配置文件，添加缓存机制"""
        # 检查缓存
        cache_key = f"config_{config_file}_{os.path.getmtime(config_file) if os.path.exists(config_file) else 0}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # 使用原有的配置加载函数
        try:
            config = read_yaml_config_env_placeholder(config_file)

            # 缓存配置
            self._config_cache[cache_key] = config

            # 限制缓存大小，避免内存泄漏
            if len(self._config_cache) > 10:
                oldest_key = next(iter(self._config_cache))
                del self._config_cache[oldest_key]

            return config

        except Exception as e:
            logging.error(f"Failed to load config file {config_file}: {e}")
            return {}

    @classmethod
    def get_instance(cls, config_file=None):
        """获取单例实例的类方法

        Args:
            config_file: 配置文件路径，仅在首次创建时有效

        Returns:
            VertexFlowService单例实例
        """
        # 如果已经存在实例，直接返回，避免重复初始化
        if cls._instance is not None:
            return cls._instance

        # 如果没有指定配置文件，使用默认路径（但不打印日志）
        if config_file is None:
            import os
            from pathlib import Path

            # 检查用户配置文件是否存在
            user_config = Path.home() / ".vertex" / "config" / "llm.yml"
            if user_config.exists():
                config_file = str(user_config)
            else:
                config_file = default_config_path("llm.yml")

        return cls(config_file)

    def get_chatmodel(self):
        """
        获取当前实例的聊天模型。

        如果实例已经包含一个模型属性，则直接返回该模型。
        否则，根据配置信息初始化并返回一个聊天模型。
        支持多模型结构，选择第一个enabled的provider中的第一个enabled的model。
        对于other类型，支持每个模型单独配置provider、base_url和sk。
        """
        if hasattr(self, "model"):
            return self.model

        # 记录llm配置信息
        logging.info("llm config : %s", self._config["llm"])

        # 过滤出启用的provider，使用安全的布尔值解析
        enabled_providers = list(
            filter(lambda value: self._parse_bool(value[1].get("enabled", False)), self._config["llm"].items())
        )
        self.model: ChatModel = None

        # 如果有provider被启用，则选择第一个enabled的provider
        if enabled_providers:
            selected_provider = enabled_providers[0]
            provider_name = selected_provider[0]
            provider_config = selected_provider[1]

            # 检查是否有models配置（多模型结构）
            if "models" in provider_config:
                # 多模型结构：选择第一个enabled的model，使用安全的布尔值解析
                models = provider_config["models"]
                enabled_models = list(filter(lambda m: self._parse_bool(m.get("enabled", False)), models))

                if enabled_models:
                    selected_model = enabled_models[0]
                    model_name = selected_model["name"]
                    logging.info("Selected model %s from provider %s", model_name, provider_name)
                else:
                    logging.warning("No enabled models found in provider %s", provider_name)
                    return None
            else:
                # 旧格式：使用model-name
                model_name = provider_config.get("model-name")
                if not model_name:
                    logging.warning("No model-name found in provider %s", provider_name)
                    return None
                logging.info("Using legacy model-name %s from provider %s", model_name, provider_name)

            # 创建模型实例
            create_params = {
                "name": model_name,
            }

            # 对于other类型，支持每个模型单独配置provider、base_url和sk
            if provider_name.lower() == "other" and "models" in provider_config:
                # 从选中的模型配置中获取参数
                if "provider" in selected_model:
                    create_params["provider"] = selected_model["provider"]
                else:
                    create_params["provider"] = "other"

                if "base_url" in selected_model:
                    create_params["base_url"] = selected_model["base_url"]
                elif "base-url" in selected_model:
                    create_params["base_url"] = selected_model["base-url"]
                else:
                    create_params["base_url"] = ""

                if "sk" in selected_model:
                    create_params["sk"] = selected_model["sk"]
                else:
                    create_params["sk"] = ""

                # 使用Other类创建实例
                self.model = create_instance(class_name="other", **create_params)
            else:
                # 其他provider使用原有逻辑
                create_params["sk"] = provider_config["sk"]

                # 为所有provider支持从配置中获取base_url
                if "base_url" in provider_config:
                    create_params["base_url"] = provider_config["base_url"]
                elif "base-url" in provider_config:
                    create_params["base_url"] = provider_config["base-url"]

                # 对于Ollama，如果没有配置base_url，使用默认值
                if provider_name.lower() == "ollama" and "base_url" not in create_params:
                    base_url = provider_config.get("base-url", "http://localhost:11434")
                    create_params["base_url"] = base_url

                # 对于豆包，不需要额外参数，使用默认配置
                if provider_name.lower() == "doubao":
                    # 豆包使用火山引擎API，不需要额外配置
                    pass

                self.model = create_instance(class_name=provider_name, **create_params)

        # 记录选定的模型信息
        if self.model is not None:
            logging.info("model selected : %s", self.model)
        else:
            logging.warning("no model selected from configuration")
        return self.model

    def get_chatmodel_by_provider(self, provider, name=None):
        """
        根据提供商获取聊天模型。

        根据给定的提供商和可选的名称，从配置中选择并创建聊天模型实例。
        支持多模型结构，可以指定具体的model名称。
        对于other类型，支持每个模型单独配置provider、base_url和sk。

        参数:
        - provider (str): 用于选择聊天模型提供商的标识符。
        - name (str, 可选): 要创建的聊天模型的名称。默认为None，将选择第一个enabled的model。

        返回:
        - ChatModel: 返回创建的聊天模型实例，如果没有找到匹配的提供商，则返回None。
        """
        # 记录llm配置信息，用于调试
        logging.debug("llm config : %s", self._config["llm"])

        # 通过提供商筛选聊天模型配置
        selected_model = list(filter(lambda value: value[0] == provider, self._config["llm"].items()))
        model: ChatModel = None
        if selected_model:
            # 如果找到了匹配的模型配置，使用第一个匹配项
            selected_model = selected_model[0]
            provider_config = selected_model[1]

            # 检查是否有models配置（多模型结构）
            if "models" in provider_config:
                models = provider_config["models"]

                if name is not None:
                    # 指定了model名称，查找匹配的model
                    target_model = None
                    for m in models:
                        if m["name"] == name:
                            target_model = m
                            break

                    if target_model is None:
                        logging.warning("Model %s not found in provider %s", name, provider)
                        return None

                    model_name = target_model["name"]
                    logging.info("Using specified model %s from provider %s", model_name, provider)
                else:
                    # 没有指定model名称，选择第一个enabled的model，使用安全的布尔值解析
                    enabled_models = list(filter(lambda m: self._parse_bool(m.get("enabled", False)), models))

                    if enabled_models:
                        target_model = enabled_models[0]
                        model_name = target_model["name"]
                        logging.info("Using first enabled model %s from provider %s", model_name, provider)
                    else:
                        logging.warning("No enabled models found in provider %s", provider)
                        return None
            else:
                # 旧格式：使用model-name
                model_name = provider_config.get("model-name")
                if not model_name:
                    logging.warning("No model-name found in provider %s", provider)
                    return None
                logging.info("Using legacy model-name %s from provider %s", model_name, provider)
                target_model = None

            # 构建创建模型实例的参数
            create_params = {
                "name": model_name,
            }

            # 对于other类型，支持每个模型单独配置provider、base_url和sk
            if provider.lower() == "other" and target_model:
                # 从模型配置中获取参数
                if "provider" in target_model:
                    create_params["provider"] = target_model["provider"]
                else:
                    create_params["provider"] = "other"

                if "base_url" in target_model:
                    create_params["base_url"] = target_model["base_url"]
                elif "base-url" in target_model:
                    create_params["base_url"] = target_model["base-url"]
                else:
                    create_params["base_url"] = ""

                if "sk" in target_model:
                    create_params["sk"] = target_model["sk"]
                else:
                    create_params["sk"] = ""

                # 使用Other类创建实例
                model = create_instance(class_name="other", **create_params)
            else:
                # 其他provider使用原有逻辑
                create_params["sk"] = provider_config["sk"]

                # 为所有provider支持从配置中获取base_url
                if "base_url" in provider_config:
                    create_params["base_url"] = provider_config["base_url"]
                elif "base-url" in provider_config:
                    create_params["base_url"] = provider_config["base-url"]

                # 对于Ollama，如果没有配置base_url，使用默认值
                if provider.lower() == "ollama" and "base_url" not in create_params:
                    base_url = provider_config.get("base-url", "http://localhost:11434")
                    create_params["base_url"] = base_url

                # 对于豆包，不需要额外参数，使用默认配置
                if provider.lower() == "doubao":
                    # 豆包使用火山引擎API，不需要额外配置
                    pass

                # 使用匹配的模型配置创建聊天模型实例
                model = create_instance(class_name=provider, **create_params)

        # 记录选定的模型信息
        if model is not None:
            logging.info("model selected : %s-%s in provider %s", model, model.model_name(), provider)
        else:
            logging.warning("no model found for provider %s", provider)
        return model

    def get_available_models(self):
        """
        获取所有可用的模型列表。

        返回:
        - list: 包含所有provider和model信息的列表
        """
        available_models = []

        for provider_name, provider_config in self._config["llm"].items():
            provider_info = {
                "provider": provider_name,
                "enabled": self._parse_bool(provider_config.get("enabled", False)),
                "models": [],
            }

            # 检查是否有models配置（多模型结构）
            if "models" in provider_config:
                for model_config in provider_config["models"]:
                    model_info = {
                        "name": model_config["name"],
                        "enabled": self._parse_bool(model_config.get("enabled", False)),
                    }
                    provider_info["models"].append(model_info)
            else:
                # 旧格式：使用model-name
                model_name = provider_config.get("model-name")
                if model_name:
                    model_info = {
                        "name": model_name,
                        "enabled": self._parse_bool(provider_config.get("enabled", False)),
                    }
                    provider_info["models"].append(model_info)

            available_models.append(provider_info)

        return available_models

    def _prompt_file_path(self, file_path):
        abs_path = "".join([self.__prompt_root_path, file_path])
        logging.info("file path %s, abs path : %s.", file_path, abs_path)
        return abs_path

    def _dify_instance_path(self, file_path):
        abs_path = "".join([self.__workflow_root_path, file_path])
        logging.info("dify yml file path %s, abs path : %s.", file_path, abs_path)
        return abs_path

    def get_service_host(self):
        return self._config["web"]["host"]

    def get_service_port(self):
        # 支持环境变量覆盖端口配置
        import os

        port = os.environ.get("VERTEX_WORKFLOW_PORT")
        if port:
            return int(port)
        return int(self._config["web"]["port"])

    def get_service_workers(self):
        return self._config["web"]["workers"]

    def get_dify_workflow_instances(self):
        instances = self._config["workflow"]["dify"]["instances"]
        if not instances:
            return []
        return [
            {
                "name": instance["name"],
                "path": self._dify_instance_path(instance["path"]),
            }
            for instance in instances
        ]

    def get_vector_engine(self, default_index=None):
        """
        根据配置信息创建并返回一个DashVector引擎实例。

        本函数从配置中提取DashVector的相关设置，包括API key、endpoint、cluster和collection，
        并使用这些信息来创建一个DashVector引擎实例。如果配置中缺少必需的信息，
        则会抛出异常。

        返回:
            DashVector: 一个DashVector引擎实例。

        抛出:
            ValueError: 如果配置中缺少API key、endpoint或cluster信息。
        """
        # 获取向量引擎配置，如果配置不存在，则使用空字典作为默认值
        vector_config = self._config.get("vector", {})
        # 从向量引擎配置中获取DashVector特定的配置
        dashvector_config = vector_config.get("dashvector", {})
        logging.info(vector_config)
        # 获取API key，如果未配置，则抛出异常
        api_key = dashvector_config.get("api-key")
        if not api_key:
            raise ValueError("API key for DashVector is missing in the configuration.")

        # 获取Endpoint，如果未配置，则抛出异常
        endpoint = dashvector_config.get("endpoint")
        if not endpoint:
            raise ValueError("Endpoint for DashVector is missing in the configuration.")

        # 获取Cluster，如果未配置，则抛出异常
        cluster = dashvector_config.get("cluster")
        if not cluster:
            raise ValueError("Cluster for DashVector is missing in the configuration.")

        # 获取Collection，如果未配置，则记录日志信息使用默认值
        collection = dashvector_config.get("collection")
        if not collection:
            logging.info("no given collection, use default.")
        if default_index:
            logging.info("no given default index, use collection.")
            collection = default_index

        # 使用获取的配置信息创建并返回DashVector引擎实例
        return DashVector(
            api_key=api_key,
            endpoint=endpoint,
            index_name=collection,
        )

    def _get_embedding_config(
        self,
        config_section,
        env_api_key,
        env_model_name,
        default_model_name,
        env_endpoint,
        default_endpoint,
        env_dimension=None,
        default_dimension=None,
    ):
        """
        通用方法，用于从配置中提取嵌入配置信息。

        参数:
        - config_section (dict): 嵌入配置的子部分。
        - env_api_key (str): 环境变量中的API key名称。
        - env_model_name (str): 环境变量中的模型名称。
        - default_model_name (str): 默认的模型名称。
        - env_endpoint (str): 环境变量中的endpoint名称。
        - default_endpoint (str): 默认的endpoint。
        - env_dimension (str): 环境变量中的维度名称。
        - default_dimension (int): 默认的维度。

        返回:
        - dict: 包含API key、模型名称、endpoint和维度的嵌入配置。

        抛出:
        - ValueError: 如果配置中缺少API key、模型名称或endpoint信息。
        """
        # 获取API key，如果未配置，则尝试从环境变量中获取
        api_key = config_section.get("api-key") or os.getenv(env_api_key)
        if not api_key:
            raise ValueError(f"API key for {env_api_key} is missing in the configuration and environment variables.")

        # 获取模型名称，如果未配置，则尝试从环境变量中获取
        model_name = config_section.get("model-name") or os.getenv(env_model_name, default_model_name)
        if not model_name:
            raise ValueError(
                f"Model name for {env_model_name} is missing in the configuration and environment variables."
            )

        # 获取endpoint，如果未配置，则尝试从环境变量中获取
        endpoint = config_section.get("endpoint") or os.getenv(env_endpoint, default_endpoint)
        if not endpoint:
            raise ValueError(f"Endpoint for {env_endpoint} is missing in the configuration and environment variables.")

        # 获取维度，如果未配置，则尝试从环境变量中获取
        dimension = config_section.get("dimension")
        if dimension is None and env_dimension:
            dimension = os.getenv(env_dimension, default_dimension)
        if dimension is None:
            dimension = default_dimension

        # 使用获取的配置信息创建并返回嵌入配置
        config = {"api_key": api_key, "model_name": model_name, "endpoint": endpoint}
        if dimension is not None:
            config["dimension"] = dimension
        return config

    def get_embedding_config(self, embedding_type=EmbeddingType.DASHSCOPE):
        """
        根据配置信息创建并返回一个嵌入配置实例。

        本函数从配置中提取嵌入的相关设置，包括API key、模型名称和endpoint，
        并使用这些信息来创建一个嵌入配置实例。如果配置中缺少必需的信息，
        则会从环境变量中获取。如果仍然缺少必需的信息，则会抛出异常。

        参数:
        - embedding_type (EmbeddingType): 嵌入提供者的类型，默认为 EmbeddingType.DASHSCOPE。

        返回:
        - dict: 包含API key、模型名称和endpoint的嵌入配置。

        抛出:
        - ValueError: 如果配置中缺少API key、模型名称或endpoint信息。
        """
        # 获取嵌入配置，如果配置不存在，则使用空字典作为默认值
        embedding_config = self._config.get("embedding", {})

        if embedding_type == EmbeddingType.DASHSCOPE:
            # 从嵌入配置中获取DashScope特定的配置
            dashscope_config = embedding_config.get("dashscope", {})
            return self._get_embedding_config(
                dashscope_config,
                "DASHSCOPE_API_KEY",
                "DASHSCOPE_MODEL_NAME",
                "text-embedding-v1",
                "DASHSCOPE_ENDPOINT",
                "https://api.dashscope.com",
            )

        elif embedding_type == EmbeddingType.BCE:
            # 从嵌入配置中获取BCE特定的配置
            bce_config = embedding_config.get("bce", {})
            return self._get_embedding_config(
                bce_config,
                "BCE_API_KEY",
                "BCE_MODEL_NAME",
                "netease-youdao/bce-embedding-base_v1",
                "BCE_ENDPOINT",
                "https://api.siliconflow.cn/v1/embeddings",
                "BCE_DIMENSION",
                768,
            )

        else:
            raise ValueError(f"Unsupported embedding type: {embedding_type}")

    def get_embedding(self, embedding_type: Optional[EmbeddingType] = None) -> TextEmbeddingProvider:
        """
        根据配置信息创建并返回一个文本嵌入提供者的实例。

        - embedding_type=None 时，自动按优先级智能选择启用的嵌入服务。
        - embedding_type=EmbeddingType.XXX 时，返回指定类型的嵌入服务。

        返回:
            TextEmbeddingProvider: 一个文本嵌入提供者的实例。

        抛出:
            ValueError: 如果没有可用的嵌入提供者。
        """
        embedding_config = self._config.get("embedding", {})

        # 智能优先级选择
        if embedding_type is None:
            if embedding_config.get("dashscope", {}).get("enabled", False):
                try:
                    return self.get_embedding(EmbeddingType.DASHSCOPE)
                except Exception as e:
                    logging.warning(f"无法创建DashScope嵌入提供者: {e}")
            if embedding_config.get("bce", {}).get("enabled", False):
                try:
                    return self.get_embedding(EmbeddingType.BCE)
                except Exception as e:
                    logging.warning(f"无法创建BCE嵌入提供者: {e}")
            if embedding_config.get("local", {}).get("enabled", True):
                try:
                    from .vertex.embedding_providers import LocalEmbeddingProvider

                    local_config = embedding_config.get("local", {})
                    return LocalEmbeddingProvider(
                        model_name=local_config.get("model_name", "all-MiniLM-L6-v2"),
                        use_mirror=local_config.get("use_mirror", True),
                        mirror_url=local_config.get("mirror_url", "https://hf-mirror.com"),
                    )
                except Exception as e:
                    logging.warning(f"无法创建本地嵌入提供者: {e}")
            raise ValueError("没有可用的嵌入提供者，请检查配置")
        # 按类型返回
        else:
            embedding_config_dict = self.get_embedding_config(embedding_type)
            if embedding_type == EmbeddingType.DASHSCOPE:
                from .vertex.embedding_providers import DashScopeEmbedding

                return DashScopeEmbedding(
                    api_key=embedding_config_dict["api_key"],
                    model_name=embedding_config_dict["model_name"],
                )
            elif embedding_type == EmbeddingType.BCE:
                from .vertex.embedding_providers import BCEEmbedding

                return BCEEmbedding(
                    api_key=embedding_config_dict["api_key"],
                    model_name=embedding_config_dict["model_name"],
                    endpoint=embedding_config_dict["endpoint"],
                    dimension=embedding_config_dict.get("dimension", 768),
                )
            else:
                raise ValueError(f"Unsupported embedding type: {embedding_type}")

    def get_web_search_config(self, provider: str = "bocha") -> Dict[str, Any]:
        """获取Web搜索配置

        Args:
            provider: 搜索提供商，默认为"bocha"

        Returns:
            dict: 包含搜索配置信息的字典
        """
        web_search_config = self._config.get("web-search", {})

        if provider == "bocha":
            # 从web-search配置中获取博查特定的配置
            bocha_config = web_search_config.get("bocha", {})

            # 获取API key，如果未配置，则尝试从环境变量中获取
            api_key = bocha_config.get("sk") or os.getenv("WEB_SEARCH_BOCHA_SK")

            # 获取启用状态
            enabled = bocha_config.get("enabled", False)

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "bing":
            # 从web-search配置中获取Bing特定的配置
            bing_config = web_search_config.get("bing", {})

            # 获取API key，如果未配置，则尝试从环境变量中获取
            api_key = bing_config.get("sk") or os.getenv("WEB_SEARCH_BING_SK")

            # 获取启用状态
            enabled = bing_config.get("enabled", False)

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "duckduckgo":
            # DuckDuckGo搜索服务（无需API密钥）
            duckduckgo_config = web_search_config.get("duckduckgo", {})

            # 获取启用状态，默认不启用（需要显式配置）
            enabled = duckduckgo_config.get("enabled", False)

            return {"enabled": enabled, "api_key": None}

        elif provider == "serpapi":
            # SerpAPI搜索服务
            serpapi_config = web_search_config.get("serpapi", {})

            # 获取API key
            api_key = serpapi_config.get("api_key") or os.getenv("WEB_SEARCH_SERPAPI_KEY")

            # 获取启用状态
            enabled = serpapi_config.get("enabled", False)

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "searchapi":
            # SearchAPI.io搜索服务
            searchapi_config = web_search_config.get("searchapi", {})

            # 获取API key
            api_key = searchapi_config.get("api_key") or os.getenv("WEB_SEARCH_SEARCHAPI_KEY")

            # 获取启用状态
            enabled = searchapi_config.get("enabled", False)

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "brave":
            # Brave Search API服务
            brave_config = web_search_config.get("brave", {})

            # 获取API key
            api_key = brave_config.get("api_key") or os.getenv("WEB_SEARCH_BRAVE_API_KEY")

            # 获取启用状态
            enabled = brave_config.get("enabled", False)

            return {"api_key": api_key, "enabled": enabled}

        else:
            raise ValueError(f"不支持的搜索提供商: {provider}")

    def get_web_search_tool(self, provider: str = "bocha"):
        """获取Web搜索工具实例

        Args:
            provider: 搜索提供商，默认为"bocha"

        Returns:
            配置好的Web搜索工具实例
        """
        from vertex_flow.workflow.tools.web_search import create_web_search_tool

        # 验证配置
        config = self.get_web_search_config(provider)
        if not config.get("enabled", False):
            raise ValueError(f"{provider}搜索服务未启用，请检查配置文件")

        # DuckDuckGo不需要API密钥
        if provider != "duckduckgo" and not config.get("api_key"):
            raise ValueError(f"{provider}搜索API密钥未配置，请检查配置文件")

        return create_web_search_tool()

    def get_finance_config(self):
        """获取金融工具配置

        Returns:
            dict: 包含金融工具配置信息的字典
        """
        finance_config = self._config.get("finance", {})

        # 获取Alpha Vantage配置
        alpha_vantage_config = finance_config.get("alpha-vantage", {})
        alpha_vantage_api_key = alpha_vantage_config.get("api-key") or os.getenv("FINANCE_ALPHA_VANTAGE_API_KEY")
        alpha_vantage_enabled = alpha_vantage_config.get("enabled", False)

        # 获取Finnhub配置
        finnhub_config = finance_config.get("finnhub", {})
        finnhub_api_key = finnhub_config.get("api-key") or os.getenv("FINANCE_FINNHUB_API_KEY")
        finnhub_enabled = finnhub_config.get("enabled", False)

        # 获取Yahoo Finance配置
        yahoo_finance_config = finance_config.get("yahoo-finance", {})
        yahoo_finance_enabled = yahoo_finance_config.get("enabled", True)

        logging.info(
            f"金融工具配置 - Alpha Vantage启用: {alpha_vantage_enabled}, API密钥已配置: {bool(alpha_vantage_api_key)}"
        )
        logging.info(f"金融工具配置 - Finnhub启用: {finnhub_enabled}, API密钥已配置: {bool(finnhub_api_key)}")
        logging.info(f"金融工具配置 - Yahoo Finance启用: {yahoo_finance_enabled}")

        return {
            "alpha_vantage": {"api_key": alpha_vantage_api_key, "enabled": alpha_vantage_enabled},
            "finnhub": {"api_key": finnhub_api_key, "enabled": finnhub_enabled},
            "yahoo_finance": {"enabled": yahoo_finance_enabled},
        }

    def get_finance_tool(self):
        """获取金融工具实例

        Returns:
            配置好的金融工具实例
        """
        from vertex_flow.workflow.tools.finance import create_finance_tool

        # 获取配置
        config = self.get_finance_config()

        # 提取API密钥
        alpha_vantage_key = None
        finnhub_key = None

        if config["alpha_vantage"]["enabled"] and config["alpha_vantage"]["api_key"]:
            alpha_vantage_key = config["alpha_vantage"]["api_key"]

        if config["finnhub"]["enabled"] and config["finnhub"]["api_key"]:
            finnhub_key = config["finnhub"]["api_key"]

        # 创建并返回金融工具实例
        # 注意：create_finance_tool() 从配置文件自动加载API密钥，无需手动传递
        return create_finance_tool()

    def get_command_line_tool(self):
        """获取命令行工具实例

        Returns:
            配置好的命令行工具实例，可执行本地命令
        """
        from vertex_flow.workflow.tools.command_line import create_command_line_tool

        # 命令行工具不需要额外配置，直接创建并返回
        return create_command_line_tool()

    def get_rerank_config(self, rerank_type="bce"):
        """
        根据配置信息创建并返回一个重排序配置实例。

        本函数从配置中提取重排序服务的相关设置，包括API key、模型名称和endpoint，
        并使用这些信息来创建一个重排序配置实例。如果配置中缺少必需的信息，
        则会从环境变量中获取。如果仍然缺少必需的信息，则会抛出异常。

        参数:
        - rerank_type (str): 重排序提供者的类型，默认为 "bce"。

        返回:
        - dict: 包含API key、模型名称和endpoint的重排序配置。

        抛出:
        - ValueError: 如果配置中缺少API key、模型名称或endpoint信息。
        """
        # 获取重排序配置，如果配置不存在，则使用空字典作为默认值
        rerank_config = self._config.get("rerank", {})

        if rerank_type == "bce":
            # 从重排序配置中获取BCE特定的配置
            bce_config = rerank_config.get("bce", {})
            return self._get_rerank_config(
                bce_config,
                "RERANK_BCE_API_KEY",
                "RERANK_BCE_MODEL_NAME",
                "netease-youdao/bce-reranker-base_v1",
                "RERANK_BCE_ENDPOINT",
                "https://api.siliconflow.cn/v1/rerank",
            )
        else:
            raise ValueError(f"Unsupported rerank type: {rerank_type}")

    def _get_rerank_config(
        self,
        config_section,
        env_api_key,
        env_model_name,
        default_model_name,
        env_endpoint,
        default_endpoint,
    ):
        """
        通用方法，用于从配置中提取重排序配置信息。

        参数:
        - config_section (dict): 重排序配置的子部分。
        - env_api_key (str): 环境变量中的API key名称。
        - env_model_name (str): 环境变量中的模型名称。
        - default_model_name (str): 默认的模型名称。
        - env_endpoint (str): 环境变量中的endpoint名称。
        - default_endpoint (str): 默认的endpoint。

        返回:
        - dict: 包含API key、模型名称和endpoint的重排序配置。

        抛出:
        - ValueError: 如果配置中缺少API key、模型名称或endpoint信息。
        """
        # 获取API key，如果未配置，则尝试从环境变量中获取
        api_key = config_section.get("api-key") or os.getenv(env_api_key)
        if not api_key:
            raise ValueError(f"API key for {env_api_key} is missing in the configuration and environment variables.")

        # 获取模型名称，如果未配置，则尝试从环境变量中获取
        model_name = config_section.get("model-name") or os.getenv(env_model_name, default_model_name)
        if not model_name:
            raise ValueError(
                f"Model name for {env_model_name} is missing in the configuration and environment variables."
            )

        # 获取endpoint，如果未配置，则尝试从环境变量中获取
        endpoint = config_section.get("endpoint") or os.getenv(env_endpoint, default_endpoint)
        if not endpoint:
            raise ValueError(f"Endpoint for {env_endpoint} is missing in the configuration and environment variables.")

        # 使用获取的配置信息创建并返回重排序配置
        return {"api_key": api_key, "model_name": model_name, "endpoint": endpoint}

    def get_vector_store_config(self, vector_type: Optional[str] = None) -> VectorConfig:
        vector_type = vector_type or "dashvector"
        vector_config = self._config.get("vector", {})

        if vector_type == "dashvector":
            dashvector_config = vector_config.get("dashvector", {})
            return self._get_vector_store_config(
                dashvector_config,
                "VECTOR_DB_SERVICE_API_KEY",
                "VECTOR_DB_ENDPOINT",
            )

        raise ValueError(f"Unsupported vector type: {vector_type}")

    def _get_vector_store_config(
        self,
        config_section,
        env_api_key,
        env_endpoint,
    ) -> VectorConfig:
        api_key = config_section.get("api-key") or os.getenv(env_api_key)
        if not api_key:
            raise ValueError(f"API key for {env_api_key} is missing in the configuration and environment variables.")

        endpoint = config_section.get("endpoint") or os.getenv(env_endpoint)
        if not endpoint:
            raise ValueError(f"Endpoint for {env_endpoint} is missing in the configuration and environment variables.")

        cluster = config_section.get("cluster")
        if not cluster:
            raise ValueError("Cluster for DashVector is missing in the configuration.")

        collection = config_section.get("collection")
        if not collection:
            raise ValueError("Collection for DashVector is missing in the configuration.")

        image_collection = config_section.get("image-collection")
        if not image_collection:
            raise ValueError("Cluster for DashVector is missing in the configuration.")

        logging.info(
            "Vector store endpoint: %s, cluster: %s, collection: %s, image_colection: %s",
            endpoint,
            cluster,
            collection,
            image_collection,
        )
        return VectorConfig(
            api_key=api_key,
            endpoint=endpoint,
            cluster=cluster,
            collection=collection,
            image_collection=image_collection,
        )

    # MCP related methods
    def get_mcp_manager(self):
        """Get MCP manager instance"""
        if not MCP_AVAILABLE:
            logging.warning("MCP functionality not available")
            return None

        mcp_manager = get_mcp_manager()

        # 如果MCP管理器还没有初始化，尝试同步初始化
        if not mcp_manager._initialized:
            try:
                mcp_config = self._config.get("mcp", {})
                if not mcp_config.get("enabled", False):
                    logging.info("MCP is disabled in configuration")
                    return mcp_manager

                # 使用线程池执行异步初始化，避免事件循环冲突
                import concurrent.futures
                import threading

                def init_mcp_sync():
                    """在独立线程中同步初始化MCP"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(mcp_manager.initialize(mcp_config))
                        logging.info("MCP Manager initialized successfully in sync mode")
                        return True
                    except Exception as e:
                        logging.error(f"Failed to initialize MCP in sync mode: {e}")
                        return False
                    finally:
                        loop.close()

                # 在独立线程中运行初始化
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(init_mcp_sync)
                    try:
                        success = future.result(timeout=30)  # 30秒超时
                        if success:
                            logging.info("MCP initialization completed successfully")
                        else:
                            logging.warning("MCP initialization failed")
                    except concurrent.futures.TimeoutError:
                        logging.error("MCP initialization timed out after 30 seconds")
                    except Exception as e:
                        logging.error(f"MCP initialization error: {e}")

            except Exception as e:
                logging.error(f"Failed to initialize MCP: {e}")

        return mcp_manager

    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration"""
        return self._config.get("mcp", {})

    def is_mcp_enabled(self) -> bool:
        """Check if MCP is enabled"""
        return MCP_AVAILABLE and self._config.get("mcp", {}).get("enabled", False)

    def get_smart_vector_engine(self):
        """
        智能选择向量引擎，根据配置优先级自动选择启用的向量服务
        并根据当前使用的嵌入提供者自动调整维度

        Returns:
            VectorEngine: 选中的向量引擎实例

        Raises:
            ValueError: 如果没有任何启用的向量引擎
        """
        vector_config = self._config.get("vector", {})

        # 优先使用云端向量引擎
        if vector_config.get("dashvector", {}).get("enabled", False):
            try:
                return self.get_vector_engine()
            except Exception as e:
                logging.warning(f"无法创建DashVector引擎: {e}")

        # 如果云端服务不可用，使用本地向量引擎
        if vector_config.get("local", {}).get("enabled", True):
            try:
                from .vertex.vector_engines import LocalVectorEngine

                local_config = vector_config.get("local", {})

                # 智能选择维度：根据当前使用的嵌入提供者
                dimension = local_config.get("dimension", 384)  # 默认维度

                # 检查当前启用的嵌入提供者，获取其维度
                embedding_config = self._config.get("embedding", {})
                if embedding_config.get("bce", {}).get("enabled", False):
                    # 如果使用 BCE 嵌入，使用其配置的维度
                    bce_dimension = embedding_config.get("bce", {}).get("dimension", 768)
                    dimension = bce_dimension
                    logging.info(f"使用 BCE 嵌入维度: {dimension}")
                elif embedding_config.get("dashscope", {}).get("enabled", False):
                    # DashScope 通常是 1536 维
                    dimension = 1536
                    logging.info(f"使用 DashScope 嵌入维度: {dimension}")
                elif embedding_config.get("local", {}).get("enabled", True):
                    # 本地嵌入使用配置的维度
                    local_embedding_dimension = embedding_config.get("local", {}).get("dimension", 384)
                    dimension = local_embedding_dimension
                    logging.info(f"使用本地嵌入维度: {dimension}")

                return LocalVectorEngine(
                    dimension=dimension,
                    index_name=local_config.get("index_name", "default"),
                    persist_dir=local_config.get("persist_dir", None),
                )
            except Exception as e:
                logging.warning(f"无法创建本地向量引擎: {e}")

        # 如果所有向量引擎都不可用，抛出异常
        raise ValueError("没有可用的向量引擎，请检查配置")
