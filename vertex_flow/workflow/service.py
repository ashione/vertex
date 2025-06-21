import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.rag_config import read_yaml_config_env_placeholder
from vertex_flow.workflow.utils import create_instance, default_config_path
from vertex_flow.workflow.vertex.vector_engines import DashVector

from .vertex.embedding_providers import BCEEmbedding, DashScopeEmbedding, TextEmbeddingProvider

logging = LoggerUtil.get_logger()


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

        参数:
        config_file (str): 配置文件的路径。如果为None，则优先使用用户配置文件，
                           如果用户配置文件不存在，则使用默认配置文件。

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
        self._config = read_yaml_config_env_placeholder(config_file)

        # 确保_config是字典类型
        if not isinstance(self._config, dict):
            raise ValueError(f"配置文件格式错误，期望字典类型，实际类型: {type(self._config)}")

        # 初始化工作流的根路径
        self.__workflow_root_path = self._config["workflow"]["dify"]["root-path"]

        # 标记为已初始化
        self._initialized = True

    @classmethod
    def get_instance(cls, config_file=None):
        """获取单例实例的类方法

        Args:
            config_file: 配置文件路径，仅在首次创建时有效

        Returns:
            VertexFlowService单例实例
        """
        if config_file is None:
            config_file = default_config_path("llm.yml")
        return cls(config_file)

    def get_chatmodel(self):
        """
        获取当前实例的聊天模型。

        如果实例已经包含一个模型属性，则直接返回该模型。
        否则，根据配置信息初始化并返回一个聊天模型。
        支持多模型结构，选择第一个enabled的provider中的第一个enabled的model。
        """
        if hasattr(self, "model"):
            return self.model

        # 记录llm配置信息
        logging.info("llm config : %s", self._config["llm"])

        # 过滤出启用的provider
        enabled_providers = list(filter(lambda value: value[1]["enabled"], self._config["llm"].items()))
        self.model: ChatModel = None

        # 如果有provider被启用，则选择第一个enabled的provider
        if enabled_providers:
            selected_provider = enabled_providers[0]
            provider_name = selected_provider[0]
            provider_config = selected_provider[1]

            # 检查是否有models配置（多模型结构）
            if "models" in provider_config:
                # 多模型结构：选择第一个enabled的model
                models = provider_config["models"]
                enabled_models = list(filter(lambda m: m.get("enabled", False), models))

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
                "sk": provider_config["sk"],
                "name": model_name,
            }

            # 对于Ollama，需要额外传递base_url参数
            if provider_name.lower() == "ollama":
                base_url = provider_config.get("base-url", "http://localhost:11434")
                create_params["base_url"] = base_url

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
                    # 没有指定model名称，选择第一个enabled的model
                    enabled_models = list(filter(lambda m: m.get("enabled", False), models))

                    if enabled_models:
                        selected_model_config = enabled_models[0]
                        model_name = selected_model_config["name"]
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

            # 构建创建模型实例的参数
            create_params = {
                "sk": provider_config["sk"],
                "name": model_name,
            }

            # 对于Ollama，需要额外传递base_url参数
            if provider.lower() == "ollama":
                base_url = provider_config.get("base-url", "http://localhost:11434")
                create_params["base_url"] = base_url

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
            provider_info = {"provider": provider_name, "enabled": provider_config.get("enabled", False), "models": []}

            # 检查是否有models配置（多模型结构）
            if "models" in provider_config:
                for model_config in provider_config["models"]:
                    model_info = {"name": model_config["name"], "enabled": model_config.get("enabled", False)}
                    provider_info["models"].append(model_info)
            else:
                # 旧格式：使用model-name
                model_name = provider_config.get("model-name")
                if model_name:
                    model_info = {"name": model_name, "enabled": provider_config.get("enabled", False)}
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

        返回:
        - dict: 包含API key、模型名称和endpoint的嵌入配置。

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

        # 使用获取的配置信息创建并返回嵌入配置
        return {"api_key": api_key, "model_name": model_name, "endpoint": endpoint}

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
                "https://api.bce.com",
            )

        else:
            raise ValueError(f"Unsupported embedding type: {embedding_type}")

    def get_embedding(self, embedding_type=EmbeddingType.DASHSCOPE) -> TextEmbeddingProvider:
        """
        根据配置信息创建并返回一个文本嵌入提供者的实例。

        本函数从配置中提取嵌入的相关设置，包括API key、模型名称和endpoint，
        并使用这些信息来创建一个 `TextEmbeddingProvider` 的具体实例。如果配置中缺少必需的信息，
        则会抛出异常。

        参数:
        - embedding_type (EmbeddingType): 嵌入提供者的类型，默认为 EmbeddingType.DASHSCOPE。

        返回:
        - TextEmbeddingProvider: 一个文本嵌入提供者的实例。

        抛出:
        - ValueError: 如果配置中缺少API key、模型名称或endpoint信息。
        """
        embedding_config = self.get_embedding_config(embedding_type)

        if embedding_type == EmbeddingType.DASHSCOPE:
            # 使用 DashScope 嵌入提供者
            return DashScopeEmbedding(
                api_key=embedding_config["api_key"],
                model_name=embedding_config["model_name"],
            )
        elif embedding_type == EmbeddingType.BCE:
            # 使用 BCE 嵌入提供者
            return BCEEmbedding(
                api_key=embedding_config["api_key"],
                model_name=embedding_config["model_name"],
                endpoint=embedding_config["endpoint"],
            )
        else:
            raise ValueError(f"Unsupported embedding type: {embedding_type}")

    def get_web_search_config(self, provider: str = "bocha") -> Dict[str, Any]:
        """获取Web搜索配置

        Args:
            provider: 搜索提供商，默认为"bocha"，支持"bocha"、"bing"、"free"

        Returns:
            包含API密钥和启用状态的配置字典

        Raises:
            ValueError: 如果配置中缺少必需信息
        """
        # 获取web-search配置，如果配置不存在，则使用空字典作为默认值
        web_search_config = self._config.get("web-search", {})

        if provider == "bocha":
            # 从web-search配置中获取博查特定的配置
            bocha_config = web_search_config.get("bocha", {})

            # 获取API key，如果未配置，则尝试从环境变量中获取
            api_key = bocha_config.get("sk") or os.getenv("WEB_SEARCH_BOCHA_SK")

            # 获取启用状态
            enabled = bocha_config.get("enabled", False)

            logging.info(f"博查搜索配置 - 启用状态: {enabled}, API密钥已配置: {bool(api_key)}")

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "bing":
            # 从web-search配置中获取Bing特定的配置
            bing_config = web_search_config.get("bing", {})

            # 获取API key，如果未配置，则尝试从环境变量中获取
            api_key = bing_config.get("sk") or os.getenv("WEB_SEARCH_BING_SK")

            # 获取启用状态
            enabled = bing_config.get("enabled", False)

            logging.info(f"Bing搜索配置 - 启用状态: {enabled}, API密钥已配置: {bool(api_key)}")

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "duckduckgo":
            # DuckDuckGo搜索服务（无需API密钥）
            duckduckgo_config = web_search_config.get("duckduckgo", {})

            # 获取启用状态，默认不启用（需要显式配置）
            enabled = duckduckgo_config.get("enabled", False)

            logging.info(f"DuckDuckGo搜索配置 - 启用状态: {enabled}")

            return {"enabled": enabled, "api_key": None}

        elif provider == "serpapi":
            # SerpAPI搜索服务
            serpapi_config = web_search_config.get("serpapi", {})

            # 获取API key
            api_key = serpapi_config.get("api_key") or os.getenv("WEB_SEARCH_SERPAPI_KEY")

            # 获取启用状态
            enabled = serpapi_config.get("enabled", False)

            logging.info(f"SerpAPI搜索配置 - 启用状态: {enabled}, API密钥已配置: {bool(api_key)}")

            return {"api_key": api_key, "enabled": enabled}

        elif provider == "searchapi":
            # SearchAPI.io搜索服务
            searchapi_config = web_search_config.get("searchapi", {})

            # 获取API key
            api_key = searchapi_config.get("api_key") or os.getenv("WEB_SEARCH_SEARCHAPI_KEY")

            # 获取启用状态
            enabled = searchapi_config.get("enabled", False)

            logging.info(f"SearchAPI搜索配置 - 启用状态: {enabled}, API密钥已配置: {bool(api_key)}")

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
