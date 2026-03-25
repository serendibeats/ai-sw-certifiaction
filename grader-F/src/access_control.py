from models import ChannelType
from exceptions import AccessDeniedError, ChannelNotFoundError, UserNotFoundError


class AccessController:
    def __init__(self, user_manager=None, channel_manager=None):
        self._user_manager = user_manager
        self._channel_manager = channel_manager

    def join_channel(self, user_id, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        if channel.channel_type == ChannelType.PRIVATE:
            if user_id not in channel.members:
                raise AccessDeniedError(f"User {user_id} cannot join private channel {channel_id}")
        channel.members.add(user_id)

    def leave_channel(self, user_id, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        channel.members.discard(user_id)

    def invite_to_channel(self, inviter_id, user_id, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        if channel.channel_type == ChannelType.PRIVATE:
            if inviter_id not in channel.members:
                raise AccessDeniedError(f"User {inviter_id} is not a member of channel {channel_id}")
        channel.members.add(user_id)

    def get_members(self, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        return list(channel.members)

    def is_member(self, user_id, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        return user_id in channel.members

    def can_access(self, user_id, channel_id):
        channel = self._channel_manager.get_channel(channel_id)
        if channel.channel_type == ChannelType.PUBLIC:
            return True
        return user_id in channel.members
