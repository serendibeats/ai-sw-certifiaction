import copy
import time


class Event:
    def __init__(self, type, data, timestamp=None):
        self.type = type
        self.data = data
        self.timestamp = timestamp if timestamp is not None else time.time()


class EventBus:
    def __init__(self):
        self._subscribers = {}
        self._history = []

    def subscribe(self, event_type, callback):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type, data):
        event = Event(type=event_type, data=copy.deepcopy(data))
        self._history.append(event)
        for callback in self._subscribers.get(event_type, []):
            callback(event)

    def get_history(self):
        return [Event(type=e.type, data=copy.deepcopy(e.data), timestamp=e.timestamp) for e in self._history]

    def get_history_by_type(self, event_type):
        return [Event(type=e.type, data=copy.deepcopy(e.data), timestamp=e.timestamp) for e in self._history if e.type == event_type]

    def clear_history(self):
        self._history.clear()

    def clear_subscribers(self):
        self._subscribers.clear()
