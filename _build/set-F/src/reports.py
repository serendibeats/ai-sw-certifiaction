from collections import Counter
from datetime import datetime


class ReportGenerator:
    def __init__(self, channel_manager=None, message_manager=None,
                 user_manager=None, search_index=None):
        self._channel_manager = channel_manager
        self._message_manager = message_manager
        self._user_manager = user_manager
        self._search_index = search_index

    def channel_activity_report(self, channel_id):
        messages = []
        if self._message_manager is not None:
            messages = self._message_manager.get_all_messages(channel_id)

        total_messages = len(messages)

        # Messages per day estimate
        if total_messages >= 2:
            timestamps = [m.created_at for m in messages]
            time_span = max(timestamps) - min(timestamps)
            days = max(time_span / 86400, 1)
            messages_per_day = total_messages / days
        elif total_messages == 1:
            messages_per_day = total_messages
        else:
            messages_per_day = 0

        # Top posters
        poster_counts = Counter(m.sender_id for m in messages)
        top_posters = poster_counts.most_common()

        # Peak hours
        hour_counts = Counter()
        for m in messages:
            hour = datetime.fromtimestamp(m.created_at).hour
            hour_counts[hour] += 1
        peak_hours = [h for h, _ in hour_counts.most_common()]

        return {
            "total_messages": total_messages,
            "messages_per_day": messages_per_day,
            "top_posters": top_posters,
            "peak_hours": peak_hours,
        }

    def user_activity_report(self, user_id):
        messages = []
        if self._message_manager is not None:
            messages = self._message_manager.get_messages_by_user(user_id)

        messages_sent = len(messages)
        channels_active = list(set(m.channel_id for m in messages))

        if messages:
            avg_message_length = sum(len(m.content) for m in messages) / messages_sent
        else:
            avg_message_length = 0

        return {
            "messages_sent": messages_sent,
            "channels_active": channels_active,
            "avg_message_length": avg_message_length,
        }

    def search_index_report(self):
        if self._search_index is None:
            return {
                "total_indexed": 0,
                "unique_terms": 0,
                "top_terms": [],
            }
        return {
            "total_indexed": self._search_index.get_index_size(),
            "unique_terms": self._search_index.get_unique_terms(),
            "top_terms": self._search_index.get_top_terms(),
        }

    def system_report(self):
        total_users = 0
        if self._user_manager is not None:
            total_users = self._user_manager.count

        total_channels = 0
        if self._channel_manager is not None:
            total_channels = self._channel_manager.count

        total_messages = 0
        if self._message_manager is not None:
            total_messages = self._message_manager.count

        # Count active channels (channels that have messages)
        active_channels = 0
        if self._channel_manager is not None and self._message_manager is not None:
            for channel in self._channel_manager.list_channels():
                msgs = self._message_manager.get_messages(channel.id)
                if len(msgs) > 0:
                    active_channels += 1

        return {
            "total_users": total_users,
            "total_channels": total_channels,
            "total_messages": total_messages,
            "active_channels": active_channels,
        }
