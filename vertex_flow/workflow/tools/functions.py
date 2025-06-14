import logging
from typing import Callable


class FunctionTool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        schema: dict = None,
        id: str = None,
    ):
        self.name = name
        self.id = id or name  # 新增唯一id，默认与name一致
        self.description = description
        self.func = func
        self.schema = schema or {}

    def execute(self, inputs: dict, context=None):
        # 打印工具调用参数
        logging.info(f"Tool '{self.name}' called with inputs: {inputs}")
        if context:
            logging.info(f"Tool '{self.name}' context: {context}")
        return self.func(inputs, context)
