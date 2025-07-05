# 常量统一管理

# 顶点类型
VERTEX_TYPE_LLM = "LLM"
VERTEX_TYPE_FUNCTION = "FUNCTION"
VERTEX_TYPE_SINK = "SINK"
VERTEX_TYPE_SOURCE = "SOURCE"
VERTEX_TYPE_EMBEDDING = "EMBEDDING"
VERTEX_TYPE_VECTOR = "VECTOR"
VERTEX_TYPE_RERANK = "RERANK"

# 通用参数 key
INPUT_KEY = "input_key"
DOCS = "docs"
QUERY = "query"
STATUS = "status"
SUCCESS = "success"
MODEL = "model"
SYSTEM = "system_message"
USER = "user_messages"
PREPROCESS = "preprocess"
POSTPROCESS = "postprocess"
ENABLE_STREAM = "enable_stream"
TMPFILE_PATH = "tmpfile_path"

# 其它常用 key
ENV_PARAMETERS = "env_parameters"
USER_PARAMETERS = "user_parameters"

# 流式输出和消息相关常量
MESSAGE_KEY = "message"
CONTENT_KEY = "content"
OUTPUT_KEY = "output"
ERROR_KEY = "error"
VERTEX_ID_KEY = "vertex_id"
TYPE_KEY = "type"
ROLE_KEY = "role"
CONVERSATION_HISTORY = "conversation_history"  # 对话历史常量

# 消息类型常量
MESSAGE_TYPE_REGULAR = "regular"
MESSAGE_TYPE_REASONING = "reasoning"
MESSAGE_TYPE_ERROR = "error"
MESSAGE_TYPE_END = "end"

# 变量定义相关常量
LOCAL_VAR = "local_var"
SOURCE_VAR = "source_var"
SOURCE_SCOPE = "source_scope"

# VertexGroup 外部source常量 - 防止与其他vertex产生overlap
SUBGRAPH_SOURCE = "__subgraph_source__"  # 标识vertex group中的外部source

# 深度研究工作流阶段常量
STAGE_TOPIC_ANALYSIS = "主题分析"
STAGE_INFORMATION_COLLECTION = "信息收集"
STAGE_DEEP_ANALYSIS = "深度分析"
STAGE_CROSS_VALIDATION = "交叉验证"

# Workflow 状态常量
WORKFLOW_COMPLETE = "workflow_complete"  # 工作流正常完成
WORKFLOW_FAILED = "workflow_failed"  # 工作流执行失败
WORKFLOW_ERROR = "workflow_error"  # 工作流执行异常

WORKFLOW_END_STATES = [WORKFLOW_COMPLETE, WORKFLOW_FAILED, WORKFLOW_ERROR]

# Reasoning configuration constants
SHOW_REASONING = True  # Default value for showing reasoning process in AI responses
SHOW_REASONING_KEY = "show_reasoning"  # Key name for show_reasoning parameter
ENABLE_REASONING_KEY = "enable_reasoning"  # Key name for enable_reasoning parameter
ENABLE_SEARCH_KEY = "enable_search"  # Key name for enable_search parameter
ENABLE_TOKEN_USAGE_KEY = "enable_token_usage"  # Key name for enable_token_usage parameter

# Content attribute constants
CONTENT_ATTR = "content"  # Attribute name for regular content
REASONING_CONTENT_ATTR = "reasoning_content"  # Attribute name for reasoning content

# Loop index constants for WhileVertex and WhileVertexGroup
ITERATION_INDEX_KEY = "iteration_index"  # Iteration index key
