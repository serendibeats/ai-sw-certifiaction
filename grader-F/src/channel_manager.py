import time
from models import Channel, ChannelType
from exceptions import ChannelNotFoundError, DuplicateChannelError


class ChannelManager:
    def __init__(self, audit_logger=None, message_manager=None):
        self._channels = {}
        self._audit_logger = audit_logger
        self._message_manager = message_manager

    def create_channel(self, name, description="", channel_type=ChannelType.PUBLIC, creator_id=None):
        for channel in self._channels.values():
            if channel.name.lower() == name.lower() and not channel.is_deleted:
                raise DuplicateChannelError(name)
        channel = Channel(name=name, description=description,
                          channel_type=channel_type, creator_id=creator_id)
        if creator_id is not None:
            channel.members.add(creator_id)
        self._channels[channel.id] = channel
        if self._audit_logger is not None:
            self._audit_logger.log("create_channel", "channel", channel.id,
                                   user_id=creator_id)
        return channel

    def get_channel(self, channel_id):
        if channel_id not in self._channels:
            raise ChannelNotFoundError(channel_id)
        channel = self._channels[channel_id]
        if channel.is_deleted:
            raise ChannelNotFoundError(channel_id)
        return channel

    def update_channel(self, channel_id, **kwargs):
        channel = self.get_channel(channel_id)
        channel.update(**kwargs)
        if self._audit_logger is not None:
            self._audit_logger.log("update_channel", "channel", channel_id)
        return channel

    def delete_channel(self, channel_id):
        if channel_id not in self._channels:
            raise ChannelNotFoundError(channel_id)
        channel = self._channels[channel_id]
        if channel.is_deleted:
            raise ChannelNotFoundError(channel_id)
        channel.is_deleted = True
        channel.deleted_at = time.time()
        if self._audit_logger is not None:
            self._audit_logger.log("delete_channel", "channel", channel_id)

    def list_channels(self):
        return [c for c in self._channels.values() if not c.is_deleted]

    def search_channels(self, query):
        query_lower = query.lower()
        return [
            channel for channel in self._channels.values()
            if query_lower in channel.name.lower() and not channel.is_deleted
        ]

    def get_channels_by_type(self, channel_type):
        return [
            channel for channel in self._channels.values()
            if channel.channel_type == channel_type and not channel.is_deleted
        ]

    def get_deleted_channels(self):
        return [c for c in self._channels.values() if c.is_deleted]

    def get_channel_stats(self, channel_id):
        channel = self.get_channel(channel_id)
        messages = []
        if self._message_manager is not None:
            messages = self._message_manager.get_messages(channel_id)
        active_users = list(set(m.sender_id for m in messages))
        last_activity = None
        if messages:
            last_activity = max(m.created_at for m in messages)
        return {
            "channel_id": channel_id,
            "name": channel.name,
            "member_count": len(channel.members),
            "message_count": len(messages),
            "active_users": active_users,
            "last_activity": last_activity,
        }

    @property
    def count(self):
        return sum(1 for c in self._channels.values() if not c.is_deleted)
