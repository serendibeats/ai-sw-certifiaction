import uuid
import time
from enum import Enum


class UserStatus(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    AWAY = "AWAY"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"


class ChannelType(Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    DIRECT = "DIRECT"


class User:
    def __init__(self, id=None, username="", display_name="", email="",
                 status=UserStatus.ONLINE, created_at=None, updated_at=None,
                 metadata=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.username = username
        self.display_name = display_name
        self.email = email
        self.status = status
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.metadata = metadata if metadata is not None else {}

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = time.time()

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Channel:
    def __init__(self, id=None, name="", description="", channel_type=ChannelType.PUBLIC,
                 creator_id=None, created_at=None, updated_at=None, metadata=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.channel_type = channel_type
        self.creator_id = creator_id
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.metadata = metadata if metadata is not None else {}
        self.members = set()
        self.is_deleted = False
        self.deleted_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "channel_type": self.channel_type.value if isinstance(self.channel_type, ChannelType) else self.channel_type,
            "creator_id": self.creator_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "members": list(self.members),
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at,
        }

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = time.time()

    def __eq__(self, other):
        if not isinstance(other, Channel):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Message:
    def __init__(self, id=None, channel_id="", sender_id="", content="",
                 created_at=None, updated_at=None, metadata=None,
                 edited=False, parent_id=None, thread_count=0):
        self.id = id if id is not None else str(uuid.uuid4())
        self.channel_id = channel_id
        self.sender_id = sender_id
        self.content = content
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.metadata = metadata if metadata is not None else {}
        self.edited = edited
        self.parent_id = parent_id
        self.thread_count = thread_count
        self.is_deleted = False
        self.deleted_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "sender_id": self.sender_id,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "edited": self.edited,
            "parent_id": self.parent_id,
            "thread_count": self.thread_count,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at,
        }

    def edit(self, new_content):
        self.content = new_content
        self.edited = True
        self.updated_at = time.time()


class Notification:
    def __init__(self, id=None, user_id="", notification_type="", content="",
                 source_id=None, read=False, created_at=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.user_id = user_id
        self.notification_type = notification_type
        self.content = content
        self.source_id = source_id
        self.read = read
        self.created_at = created_at if created_at is not None else time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "content": self.content,
            "source_id": self.source_id,
            "read": self.read,
            "created_at": self.created_at,
        }


class AuditEntry:
    def __init__(self, id=None, action="", entity_type="", entity_id="",
                 user_id=None, details=None, timestamp=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.user_id = user_id
        self.details = details if details is not None else {}
        self.timestamp = timestamp if timestamp is not None else time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }
