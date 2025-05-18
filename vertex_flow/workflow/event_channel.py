from collections import defaultdict
from threading import Lock
import queue

class EventChannel:
    def __init__(self):
        self.event_channels = defaultdict(list)  # event_type -> [callback, ...]
        self.event_queues = defaultdict(queue.Queue)  # event_type -> queue
        self.event_lock = Lock()

    def emit_event(self, event_type: str, event_data: dict):
        """分发事件到所有监听器，并放入事件队列"""
        with self.event_lock:
            for callback in self.event_channels[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    # 可以根据需要添加日志
                    pass
            self.event_queues[event_type].put(event_data)

    def subscribe(self, event_type: str, callback):
        """注册事件监听器"""
        with self.event_lock:
            self.event_channels[event_type].append(callback)