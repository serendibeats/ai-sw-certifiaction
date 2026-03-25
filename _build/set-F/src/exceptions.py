class UserNotFoundError(Exception):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class ChannelNotFoundError(Exception):
    def __init__(self, channel_id):
        self.channel_id = channel_id
        super().__init__(f"Channel not found: {channel_id}")


class MessageNotFoundError(Exception):
    def __init__(self, message_id):
        self.message_id = message_id
        super().__init__(f"Message not found: {message_id}")


class DuplicateUserError(Exception):
    def __init__(self, username):
        self.username = username
        super().__init__(f"Duplicate user: {username}")


class DuplicateChannelError(Exception):
    def __init__(self, channel_name):
        self.channel_name = channel_name
        super().__init__(f"Duplicate channel: {channel_name}")


class InvalidMessageError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class InvalidChannelError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class AccessDeniedError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class RateLimitError(Exception):
    def __init__(self, user_id, message):
        self.user_id = user_id
        self.message = message
        super().__init__(message)


class EncryptionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
