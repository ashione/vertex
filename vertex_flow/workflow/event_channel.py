from collections import defaultdict
from threading import Lock
import queue
import asyncio
from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger()


class EventChannel:
    def __init__(self):
        self.event_channels = defaultdict(list)  # event_type -> [callback, ...]
        self.event_queues = defaultdict(queue.Queue)  # event_type -> queue
        self.event_lock = Lock()

        # 提前生成三个事件通道
        self.event_queues["messages"] = queue.Queue()
        self.event_queues["values"] = queue.Queue()
        self.event_queues["updates"] = queue.Queue()

    def emit_event(self, event_type: str, event_data: dict):
        """分发事件到所有监听器，并放入事件队列"""
        logger.debug(f"Emitting event: {event_type}")  # Add this line for logging inf
        with self.event_lock:
            for callback in self.event_channels[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
            logger.debug(f"Event emitted: {event_data}")  # Add this line for loggin
            self.event_queues[event_type].put(event_data)

    async def astream(self, event_type: str):
        """异步生成器，支持 async for 语法"""
        while True:
            logger.debug(f"Event waiting: event_type={event_type}")
            event_data = await asyncio.to_thread(self.event_queues[event_type].get)
            logger.info(f"Event received: {event_data}")
            yield event_data
            # 检查事件类型是否为 workflow_complete，如果是则结束生成器
            if event_data.get("status") == "end":
                break

    def subscribe(self, event_type: str, callback):
        """注册事件监听器"""
        with self.event_lock:
            self.event_channels[event_type].append(callback)
