import asyncio
from collections import defaultdict
from threading import Lock

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import WORKFLOW_END_STATES

logger = LoggerUtil.get_logger()


# 事件类型枚举
class EventType:
    """定义支持的事件类型常量"""

    MESSAGES = "messages"  # 消息事件：用于传递文本消息、状态更新等
    VALUES = "values"  # 值事件：用于传递计算结果、数据值等
    UPDATES = "updates"  # 更新事件：用于传递进度更新、状态变化等


class EventChannel:
    """
    事件通道类：提供异步事件发布订阅机制

    主要功能：
    1. 支持多种事件类型的发布和订阅
    2. 提供异步流式事件监听（astream）
    3. 支持workflow_complete事件的特殊处理
    4. 智能退出策略，避免无限等待
    5. 线程安全的事件分发

    使用场景：
    - 工作流执行过程中的事件通信
    - 异步任务状态监控
    - 实时数据流处理
    """

    def __init__(self, max_empty_duration=10.0, queue_timeout=0.1):
        """
        初始化事件通道

        Args:
            max_empty_count (int): 最大连续空事件计数，默认100次
                当连续检查到空事件超过此次数时，触发退出策略
            max_empty_duration (float): 最大空事件持续时间（秒），默认10.0秒
                当空事件持续时间超过此值时，触发退出策略
            queue_timeout (float): 队列获取超时时间（秒），默认0.1秒
                单次队列获取操作的超时时间
        """
        # 事件回调存储：event_type -> [callback, ...]
        # 用于同步事件分发给注册的回调函数
        self.event_channels = defaultdict(list)

        # 异步事件队列：event_type -> asyncio.Queue
        # 用于异步流式事件处理
        self.event_queues = defaultdict(asyncio.Queue)

        # 线程锁：保证事件分发的线程安全
        self.event_lock = Lock()

        # 智能退出策略配置参数
        self.max_empty_duration = max_empty_duration
        self.queue_timeout = queue_timeout

        # 预创建三个标准事件队列，提高性能
        self.event_queues[EventType.MESSAGES] = asyncio.Queue()
        self.event_queues[EventType.VALUES] = asyncio.Queue()
        self.event_queues[EventType.UPDATES] = asyncio.Queue()

    def set_wait_time(self, wait_time: float):
        """
        设置等待时间

        Args:
            wait_time (float): 等待时间（秒）
        """
        self.max_empty_duration = wait_time
        logger.info(f"Set wait time to {wait_time} seconds")

    def emit_event(self, event_type, event_data):
        """
        发送事件到指定类型的通道

        此方法是线程安全的，支持同时向同步回调和异步队列分发事件。

        Args:
            event_type (str): 事件类型，应为EventType中定义的常量
            event_data (any): 事件数据，可以是任意类型的数据

        处理流程：
        1. 获取线程锁确保线程安全
        2. 遍历并调用所有注册的同步回调函数
        3. 将事件数据放入对应的异步队列
        4. 异常处理：回调异常不影响其他回调，队列满时记录警告
        """
        with self.event_lock:
            # 同步回调处理：立即执行所有注册的回调函数
            for callback in self.event_channels[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    # 单个回调异常不应影响其他回调的执行
                    logger.error(f"Error in event callback: {e}")

            # 异步队列处理：将事件放入队列供异步消费
            if event_type in self.event_queues:
                try:
                    # 使用put_nowait避免阻塞，如果队列满则抛出异常
                    self.event_queues[event_type].put_nowait(event_data)
                except asyncio.QueueFull:
                    # 队列满时记录警告但不阻塞程序执行
                    logger.warning(f"Queue full for event type {event_type}, dropping event")

    async def astream(self, event_types):
        """
        异步流式获取指定类型的事件

        这是EventChannel的核心方法，提供异步流式事件监听功能。
        支持同时监听多种事件类型，并实现智能退出策略。

        Args:
            event_types (list): 要监听的事件类型列表，如[EventType.MESSAGES, EventType.VALUES]

        Yields:
            event_data: 接收到的事件数据，按接收顺序yield

        特性：
        1. 并发监听：同时监听多个事件队列
        2. 智能退出：基于空事件持续时间的退出策略
        3. workflow状态处理：处理workflow_complete和workflow_failed两种结束状态
        4. 异常安全：妥善处理取消和异常情况

        退出条件：
        - 接收到workflow_complete或workflow_failed事件且所有队列为空
        - 空事件持续时间超过max_empty_duration秒
        """
        # 统一处理为列表格式：支持单个事件类型或事件类型列表
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

        current_tasks = []
        # 智能退出策略相关变量
        empty_start_time = None  # 空事件开始时间
        workflow_complete_event = None  # 暂存workflow状态事件，等待合适时机发送
        workflow_ended = False  # 标记workflow是否已结束（包括完成和失败）

        try:
            while True:
                logger.debug(f"Event waiting: event_types={event_types}")

                # 创建所有事件类型的等待任务
                current_tasks = [asyncio.create_task(get_event_from_queue(event_type)) for event_type in event_types]

                try:
                    # 等待所有任务完成
                    done, _ = await asyncio.wait(current_tasks, return_when=asyncio.ALL_COMPLETED)

                    # 处理所有完成的任务
                    has_valid_event = False
                    events_to_yield = []

                    for task in done:
                        try:
                            event_type, event_data = await task
                            if event_data is not None:  # 忽略超时返回的None
                                has_valid_event = True
                                logger.debug(f"Event received from {event_type}: {event_data}")

                                # 检查是否收到 workflow 状态事件
                                status = event_data.get("status")
                                if status in WORKFLOW_END_STATES:
                                    workflow_ended = True
                                    workflow_complete_event = event_data
                                    logger.info(
                                        f"Workflow {status} event received, will be deferred until other queues are empty"
                                    )
                                    # 不立即yield，而是暂存起来
                                else:
                                    # 非workflow状态事件加入待yield列表
                                    events_to_yield.append(event_data)
                        except Exception as e:
                            logger.error(f"Error processing task result: {e}")

                    # yield所有非workflow状态事件
                    for event_data in events_to_yield:
                        yield event_data
                        logger.debug(f"Event yielded: {event_data}")

                    # 如果没有找到有效事件，短暂等待
                    if not has_valid_event:
                        await asyncio.sleep(self.queue_timeout)

                    # 检查是否应该发送暂存的workflow状态事件
                    if workflow_complete_event:
                        # 检查除了UPDATES队列外的其他队列是否为空
                        other_event_types = [et for et in event_types if et != EventType.UPDATES]
                        other_queues_empty = all(self.event_queues[et].empty() for et in other_event_types)

                        if other_queues_empty:
                            # 其他队列都空了，现在可以发送workflow状态事件
                            logger.info("Other queues empty, now yielding workflow status event")
                            yield workflow_complete_event
                            logger.debug(f"Workflow status event yielded: {workflow_complete_event}")
                            break
                        else:
                            logger.info(
                                "Workflow ended but other queues not empty, continuing to process remaining events"
                            )
                            # 继续处理剩余事件，不退出循环

                    # 智能退出策略：基于工作流状态和超时机制
                    all_queues_empty = all(self.event_queues[et].empty() for et in event_types)

                    if not has_valid_event and all_queues_empty:
                        # 初始化或更新空事件计数和时间戳
                        current_time = asyncio.get_event_loop().time()
                        if empty_start_time is None:
                            empty_start_time = current_time
                            empty_count = 0
                        else:
                            empty_count += 1

                        empty_duration = current_time - empty_start_time

                        # 退出条件：
                        # 1. 空事件持续时间超过配置的最大时长
                        # 2. 且所有队列确实为空
                        # 3. 但如果还没收到workflow状态事件，则延长等待时间
                        max_duration = self.max_empty_duration if workflow_ended else self.max_empty_duration * 2
                        if empty_duration > max_duration and all_queues_empty:
                            logger.info(
                                f"No events for extended period (count: {empty_count}, duration: {empty_duration:.2f}s), stopping stream"
                            )
                            break
                    else:
                        # 重置空事件计数器
                        empty_start_time = None
                        empty_count = 0

                    # 如果收到 workflow 状态事件，且所有队列都为空，则退出
                    if workflow_ended and all_queues_empty:
                        logger.info("Workflow ended and all queues are empty, stopping event channel")
                        break

                except Exception as e:
                    # 取消所有任务
                    for task in current_tasks:
                        if not task.done():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    raise e

                except asyncio.CancelledError:
                    # 如果整个等待被取消，确保清理当前任务
                    for task in current_tasks:
                        if not task.done():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    if current_tasks:
                        await asyncio.gather(*current_tasks, return_exceptions=True)
                    raise

        except Exception as e:
            logger.error(f"Error in astream: {e}")
        finally:
            # 确保所有任务都被取消
            for task in current_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            if current_tasks:
                await asyncio.gather(*current_tasks, return_exceptions=True)

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
        """
        注册事件监听器

        为指定事件类型注册同步回调函数。当该类型的事件被emit时，
        所有注册的回调函数都会被立即调用。

        Args:
            event_type (str): 事件类型，应为EventType中定义的常量
            callback (callable): 回调函数，接收event_data作为参数

        注意：
        - 回调函数是同步执行的，应避免耗时操作
        - 回调函数中的异常不会影响其他回调的执行
        - 此方法是线程安全的
        """
        with self.event_lock:
            self.event_channels[event_type].append(callback)

    async def get_event_from_queue(self, event_type):
        """
        从指定队列获取事件

        这是一个异步方法，用于从事件队列中获取事件数据。
        采用两阶段获取策略：先尝试立即获取，失败则等待超时。

        Args:
            event_type (str): 事件类型

        Returns:
            event_data: 获取到的事件数据，如果超时则返回None

        获取策略：
        1. 首先检查队列是否为空，非空则立即获取
        2. 如果队列为空，使用超时等待机制
        3. 超时后返回None，避免无限阻塞
        """
        queue = self.event_queues[event_type]

        # 第一阶段：尝试立即获取（避免不必要的等待）
        if not queue.empty():
            try:
                return queue.get_nowait()
            except asyncio.QueueEmpty:
                # 队列在检查后被其他协程清空，继续到第二阶段
                pass

        # 第二阶段：超时等待获取
        try:
            return await asyncio.wait_for(queue.get(), timeout=self.queue_timeout)
        except asyncio.TimeoutError:
            # 超时返回None，让调用方知道没有事件
            return None

    def all_queues_empty_except_updates(self, event_types):
        """
        检查除了UPDATES队列外的其他队列是否都为空

        这是workflow_complete事件处理的辅助方法。
        UPDATES队列通常包含进度更新等非关键事件，
        在判断工作流是否完成时可以忽略。

        Args:
            event_types (list): 要检查的事件类型列表

        Returns:
            bool: 如果除UPDATES外的所有队列都为空则返回True

        用途：
        - 决定何时发送workflow_complete事件
        - 确保重要事件都已处理完毕
        """
        for event_type in event_types:
            if event_type != EventType.UPDATES and event_type in self.event_queues:
                if not self.event_queues[event_type].empty():
                    return False
        return True
