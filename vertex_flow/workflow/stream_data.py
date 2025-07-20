from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class StreamDataType(Enum):
    """流式数据类型枚举"""

    CONTENT = "content"
    REASONING = "reasoning"
    TOOL_CALLS = "tool_calls"
    ERROR = "error"
    USAGE = "usage"


@dataclass
class StreamData:
    """流式数据的标准化结构"""

    type: StreamDataType
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证数据完整性"""
        if self.type == StreamDataType.CONTENT and self.content is None:
            raise ValueError("Content type requires content field")
        elif self.type == StreamDataType.REASONING and self.content is None:
            raise ValueError("Reasoning type requires content field")
        elif self.type == StreamDataType.TOOL_CALLS and not self.tool_calls:
            raise ValueError("Tool calls type requires tool_calls field")
        elif self.type == StreamDataType.ERROR and self.error is None:
            raise ValueError("Error type requires error field")

    @classmethod
    def create_content(cls, content: str, usage: Optional[Dict[str, Any]] = None) -> "StreamData":
        """创建内容类型的流式数据"""
        return cls(type=StreamDataType.CONTENT, content=content, usage=usage)

    @classmethod
    def create_reasoning(cls, content: str, usage: Optional[Dict[str, Any]] = None) -> "StreamData":
        """创建推理类型的流式数据"""
        return cls(type=StreamDataType.REASONING, content=content, usage=usage)

    @classmethod
    def create_tool_calls(
        cls, tool_calls: List[Dict[str, Any]], usage: Optional[Dict[str, Any]] = None
    ) -> "StreamData":
        """创建工具调用类型的流式数据"""
        return cls(type=StreamDataType.TOOL_CALLS, tool_calls=tool_calls, usage=usage)

    @classmethod
    def create_error(cls, error: str, usage: Optional[Dict[str, Any]] = None) -> "StreamData":
        """创建错误类型的流式数据"""
        return cls(type=StreamDataType.ERROR, error=error, usage=usage)

    @classmethod
    def create_usage(cls, usage: Dict[str, Any]) -> "StreamData":
        """创建使用统计类型的流式数据"""
        return cls(type=StreamDataType.USAGE, usage=usage)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（向后兼容）"""
        result = {"type": self.type.value}

        if self.content is not None:
            result["content"] = self.content
        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls
        if self.error is not None:
            result["error"] = self.error
        if self.usage is not None:
            result["usage"] = self.usage
        if self.metadata is not None:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamData":
        """从字典创建StreamData对象（向后兼容）"""
        data_type = StreamDataType(data.get("type"))

        return cls(
            type=data_type,
            content=data.get("content"),
            tool_calls=data.get("tool_calls") or data.get("data") if data_type == StreamDataType.TOOL_CALLS else None,
            error=data.get("error") or data.get("data") if data_type == StreamDataType.ERROR else None,
            usage=data.get("usage"),
            metadata=data.get("metadata"),
        )

    def get_data(self) -> Any:
        """获取主要数据内容（向后兼容）"""
        if self.type == StreamDataType.CONTENT or self.type == StreamDataType.REASONING:
            return self.content
        elif self.type == StreamDataType.TOOL_CALLS:
            return self.tool_calls
        elif self.type == StreamDataType.ERROR:
            return self.error
        elif self.type == StreamDataType.USAGE:
            return self.usage
        return None
