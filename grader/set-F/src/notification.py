from models import Notification


class NotificationManager:
    def __init__(self, user_manager=None, access_controller=None):
        self._user_manager = user_manager
        self._access_controller = access_controller
        self._notifications = {}  # notification_id -> Notification
        self._user_notifications = {}  # user_id -> [notification_id, ...]

    @property
    def user_manager(self):
        return self._user_manager

    def notify(self, user_id, notification_type, content, source_id=None):
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            content=content,
            source_id=source_id,
        )
        self._notifications[notification.id] = notification
        if user_id not in self._user_notifications:
            self._user_notifications[user_id] = []
        self._user_notifications[user_id].append(notification.id)
        return notification

    def get_notifications(self, user_id):
        if user_id not in self._user_notifications:
            return []
        return [self._notifications[nid] for nid in self._user_notifications[user_id]
                if nid in self._notifications]

    def get_unread_count(self, user_id):
        notifications = self.get_notifications(user_id)
        return sum(1 for n in notifications if not n.read)

    def mark_read(self, notification_id):
        if notification_id in self._notifications:
            self._notifications[notification_id].read = True

    def mark_all_read(self, user_id):
        for notification in self.get_notifications(user_id):
            notification.read = True

    def clear_notifications(self, user_id):
        if user_id in self._user_notifications:
            for nid in self._user_notifications[user_id]:
                if nid in self._notifications:
                    del self._notifications[nid]
            del self._user_notifications[user_id]
