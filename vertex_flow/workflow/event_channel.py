import asyncio
from collections import defaultdict
from threading import Lock

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger()


# 事件类型枚举
class EventType:
    MESSAGES = "messages"
    VALUES = "values"
    UPDATES = "updates"


class EventChannel:
    def __init__(self, max_empty_count=100, max_empty_duration=10.0, queue_timeout=0.5):
        """
        初始化事件通道

        Args:
            max_empty_count: 最大连续空事件计数，默认100次
            max_empty_duration: 最大空事件持续时间（秒），默认10.0秒
            queue_timeout: 队列获取超时时间（秒），默认0.5秒
        """
        self.event_channels = defaultdict(list)  # event_type -> [callback, ...]
        self.event_queues = defaultdict(asyncio.Queue)  # event_type -> asyncio.Queue
        self.event_lock = Lock()

        # 配置参数
        self.max_empty_count = max_empty_count
        self.max_empty_duration = max_empty_duration
        self.queue_timeout = queue_timeout

        # 提前生成三个事件通道
        self.event_queues[EventType.MESSAGES] = asyncio.Queue()
        self.event_queues[EventType.VALUES] = asyncio.Queue()
        self.event_queues[EventType.UPDATES] = asyncio.Queue()

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
            self.event_queues[event_type].put_nowait(event_data)

    async def astream(self, event_types):
        """异步生成器，支持订阅多种类型的事件，支持 async for 语法

        Args:
            event_types: 可以是单个事件类型字符串，或者事件类型列表
        """
        # 统一处理为列表格式
        if isinstance(event_types, str):
            event_types = [event_types]

        logger.debug(f"astream called with event_types: {event_types}")

        # 创建任务列表，每个事件类型对应一个任务
        async def get_event_from_queue(event_type):
            try:
                # 先检查队列是否为空，如果不为空立即获取
                if not self.event_queues[event_type].empty():
                    event_data = await self.event_queues[event_type].get()
                    return event_type, event_data

                # 队列为空时使用超时机制等待
                event_data = await asyncio.wait_for(self.event_queues[event_type].get(), timeout=self.queue_timeout)
                return event_type, event_data
            except asyncio.TimeoutError:
                # 超时时返回None，让外层循环继续
                return event_type, None
            except asyncio.CancelledError:
                logger.debug(f"Task for {event_type} was cancelled")
                raise
            except Exception as e:
                logger.error(f"Error getting event from queue {event_type}: {e}")
                raise

        tasks = []
        try:
            while True:
                logger.debug(f"Event waiting: event_types={event_types}")

                # 创建所有事件类型的等待任务
                tasks = [asyncio.create_task(get_event_from_queue(event_type)) for event_type in event_types]

                # 等待任何一个事件到达
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                # 处理完成的任务 - 确保流式输出，每次只处理一个事件
                workflow_complete = False
                has_valid_event = False

                # 只处理第一个有效的已完成任务
                for task in done:
                    try:
                        event_type, event_data = await task

                        # 跳过超时返回的None事件
                        if event_data is None:
                            continue

                        # 找到第一个有效事件就处理并退出循环
                        has_valid_event = True
                        logger.info(f"Event received from {event_type}: {event_data}")
                        logger.debug(f"About to yield event: {event_data}")

                        # 检查是否收到 workflow_complete 事件
                        if event_data.get("status") == "workflow_complete":
                            workflow_complete = True

                        yield event_data
                        logger.debug(f"Event yielded: {event_data}")
                        break  # 处理完一个事件就退出，确保流式输出

                    except asyncio.CancelledError:
                        logger.debug(f"Task was cancelled during processing")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")

                # 取消所有待处理的任务
                for task in pending:
                    task.cancel()

                # 等待所有任务完成取消
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

                # 如果收到 workflow_complete 事件，退出循环
                if workflow_complete:
                    logger.info("Workflow completed, stopping event stream")
                    break

                # 智能退出策略：基于工作流状态和超时机制
                all_queues_empty = all(self.event_queues[et].empty() for et in event_types)

                if not has_valid_event and all_queues_empty and len(done) > 0:
                    # 初始化或更新空事件计数和时间戳
                    current_time = asyncio.get_event_loop().time()
                    if not hasattr(self, "_empty_start_time"):
                        self._empty_start_time = current_time
                        self._empty_count = 0

                    self._empty_count += 1
                    empty_duration = current_time - self._empty_start_time

                    # 退出条件：
                    # 1. 连续空事件超过配置的最大次数
                    # 2. 或者空事件持续时间超过配置的最大时长
                    # 3. 且所有队列确实为空
                    if (
                        self._empty_count > self.max_empty_count or empty_duration > self.max_empty_duration
                    ) and all_queues_empty:
                        logger.info(
                            f"No events for extended period (count: {self._empty_count}, duration: {empty_duration:.2f}s), stopping stream"
                        )
                        break
                else:
                    # 重置空事件计数器
                    if hasattr(self, "_empty_start_time"):
                        delattr(self, "_empty_start_time")
                    self._empty_count = 0

        except Exception as e:
            logger.error(f"Error in astream: {e}")
        finally:
            # 确保所有任务都被取消
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # 清空所有事件队列，确保没有残留事件阻止程序退出
            for event_type in event_types:
                if event_type in self.event_queues:
                    queue = self.event_queues[event_type]
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

            logger.debug("All tasks cleaned up and queues cleared in astream")

    def subscribe(self, event_type: str, callback):
        """注册事件监听器"""
        with self.event_lock:
            self.event_channels[event_type].append(callback)
