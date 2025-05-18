import dashvector
import abc
from vertex_flow.utils.logger import LoggerUtil
from typing import List, Any, Dict

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
        插入文档到指定索引中。

        如果docs是单个文档，则将其转换为列表
        """
        # 检查docs是否为列表，如果不是，则将其转换为列表
        if not isinstance(docs, list):
            docs = [docs]

        if len(docs) <= 0:
            logger.warning("No documents to insert.")
            return

        # 调用get_index方法获取索引，并插入文档
        try:
            if isinstance(docs[0], Doc):
                # 处理 Doc 对象
                self.get_index(index_name).insert(
                    [(doc.id, doc.vector, doc.fields) for doc in docs]
                )
            elif isinstance(docs, (list, tuple)) and all(
                isinstance(x, (int, float)) for x in docs
            ):
                # 处理 float 向量
                self.get_index(index_name).insert((docs,))
            else:
                raise ValueError(f"Unsupported document type: {type(docs[0])}")
        except Exception as e:
            logger.warning(f"insert failed: {e}")
            raise e

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
                logger.error(
                    f"Failed to create index {index_name}. Response: {response}"
                )
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
                logger.error(
                    f"Failed to delete index {index_name}. Response: {response}"
                )
                return False
        except Exception as e:
            logger.error(f"Exception occurred while deleting index {index_name}: {e}")
            return False
