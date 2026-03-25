import time
import copy
from models import Message
from exceptions import MessageNotFoundError, ChannelNotFoundError, AccessDeniedError, RateLimitError, InvalidMessageError


class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = {}  # user_id -> [timestamps]

    def _clean(self, user_id):
        now = time.time()
        if user_id in self._requests:
            self._requests[user_id] = [
                t for t in self._requests[user_id]
                if now - t < self.window_seconds
            ]

    def check(self, user_id):
        self._clean(user_id)
        if user_id not in self._requests:
            return True
        return len(self._requests[user_id]) < self.max_requests

    def record(self, user_id):
        if user_id not in self._requests:
            self._requests[user_id] = []
        self._requests[user_id].append(time.time())

    def get_remaining(self, user_id):
        self._clean(user_id)
        if user_id not in self._requests:
            return self.max_requests
        return max(0, self.max_requests - len(self._requests[user_id]))


class MessageManager:
    def __init__(self, channel_manager=None, mention_parser=None,
                 notification_manager=None, access_controller=None,
                 rate_limiter=None, search_index=None,
                 encryption_manager=None, audit_logger=None,
                 forbidden_words=None):
        self._channel_manager = channel_manager
        self._mention_parser = mention_parser
        self._notification_manager = notification_manager
        self._access_controller = access_controller
        self._rate_limiter = rate_limiter
        self._search_index = search_index
        self._encryption_manager = encryption_manager
        self._audit_logger = audit_logger
        self._forbidden_words = forbidden_words or []
        self._messages = {}

    def _validate_content(self, content):
        if not content or not content.strip():
            raise InvalidMessageError("Message content cannot be empty")
        if len(content) > 10000:
            raise InvalidMessageError("Message content exceeds maximum length of 10000 characters")

    def _check_forbidden_words(self, content, message):
        if self._forbidden_words:
            content_lower = content.lower()
            found = [w for w in self._forbidden_words if w.lower() in content_lower]
            if found:
                if "warnings" not in message.metadata:
                    message.metadata["warnings"] = []
                message.metadata["warnings"].extend(found)

    def _decrypt_message(self, msg):
        """Return a new Message object with decrypted content."""
        if self._encryption_manager is not None and self._encryption_manager.is_encrypted(msg.content):
            decrypted = copy.copy(msg)
            decrypted.content = self._encryption_manager.decrypt(msg.content)
            return decrypted
        return msg

    def send_message(self, channel_id, sender_id, content):
        self._validate_content(content)
        if self._channel_manager is not None:
            self._channel_manager.get_channel(channel_id)
        if self._access_controller is not None:
            if not self._access_controller.can_access(sender_id, channel_id):
                raise AccessDeniedError(f"User {sender_id} cannot access channel {channel_id}")
        if self._rate_limiter is not None:
            if not self._rate_limiter.check(sender_id):
                raise RateLimitError(sender_id, f"Rate limit exceeded for user {sender_id}")
            self._rate_limiter.record(sender_id)

        plaintext = content
        stored_content = content
        if self._encryption_manager is not None:
            stored_content = self._encryption_manager.encrypt(content)

        message = Message(channel_id=channel_id, sender_id=sender_id, content=stored_content)
        self._check_forbidden_words(plaintext, message)
        self._messages[message.id] = message

        # Index with plaintext
        if self._search_index is not None:
            index_msg = copy.copy(message)
            index_msg.content = plaintext
            self._search_index.index_message(index_msg)

        # Audit log
        if self._audit_logger is not None:
            self._audit_logger.log("send_message", "message", message.id,
                                   user_id=sender_id)

        if self._mention_parser is not None and self._notification_manager is not None:
            mentioned_usernames = self._mention_parser.parse(plaintext)
            user_manager = self._notification_manager.user_manager
            if user_manager is not None:
                for username in mentioned_usernames:
                    try:
                        user = user_manager.get_user_by_username(username)
                        self._notification_manager.notify(
                            user.id, "mention", plaintext, source_id=message.id
                        )
                    except Exception:
                        pass

            # Handle @all mentions
            all_mentions = self._mention_parser.parse_all_mentions(plaintext)
            if all_mentions and self._access_controller is not None:
                members = self._access_controller.get_members(channel_id)
                for member_id in members:
                    if member_id != sender_id:
                        self._notification_manager.notify(
                            member_id, "mention_all", plaintext, source_id=message.id
                        )

        return self._decrypt_message(message)

    def get_message(self, message_id):
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        msg = self._messages[message_id]
        if msg.is_deleted:
            raise MessageNotFoundError(message_id)
        return self._decrypt_message(msg)

    def edit_message(self, message_id, new_content):
        self._validate_content(new_content)
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        message = self._messages[message_id]
        if message.is_deleted:
            raise MessageNotFoundError(message_id)

        plaintext = new_content
        stored_content = new_content
        if self._encryption_manager is not None:
            stored_content = self._encryption_manager.encrypt(new_content)

        message.edit(stored_content)
        self._check_forbidden_words(plaintext, message)

        if self._search_index is not None:
            index_msg = copy.copy(message)
            index_msg.content = plaintext
            self._search_index.update_message(index_msg)

        if self._audit_logger is not None:
            self._audit_logger.log("edit_message", "message", message_id,
                                   user_id=message.sender_id)

        return self._decrypt_message(message)

    def delete_message(self, message_id):
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        msg = self._messages[message_id]
        if msg.is_deleted:
            raise MessageNotFoundError(message_id)
        msg.is_deleted = True
        msg.deleted_at = time.time()
        if self._search_index is not None:
            self._search_index.remove_message(message_id)
        if self._audit_logger is not None:
            self._audit_logger.log("delete_message", "message", message_id,
                                   user_id=msg.sender_id)

    def get_messages(self, channel_id):
        if self._channel_manager is not None:
            self._channel_manager.get_channel(channel_id)
        messages = [self._decrypt_message(m) for m in self._messages.values()
                    if m.channel_id == channel_id and m.parent_id is None and not m.is_deleted]
        return sorted(messages, key=lambda m: m.created_at)

    def get_all_messages(self, channel_id):
        if self._channel_manager is not None:
            self._channel_manager.get_channel(channel_id)
        messages = [self._decrypt_message(m) for m in self._messages.values()
                    if m.channel_id == channel_id and not m.is_deleted]
        return sorted(messages, key=lambda m: m.created_at)

    def get_messages_by_user(self, user_id):
        return [self._decrypt_message(m) for m in self._messages.values()
                if m.sender_id == user_id and not m.is_deleted]

    def search_messages(self, query):
        if self._search_index is not None:
            message_ids = self._search_index.search(query)
            results = []
            for mid in message_ids:
                if mid in self._messages and not self._messages[mid].is_deleted:
                    results.append(self._decrypt_message(self._messages[mid]))
            return results
        query_lower = query.lower()
        results = []
        for m in self._messages.values():
            if m.is_deleted:
                continue
            decrypted = self._decrypt_message(m)
            if query_lower in decrypted.content.lower():
                results.append(decrypted)
        return results

    def get_deleted_messages(self, channel_id):
        return [m for m in self._messages.values()
                if m.channel_id == channel_id and m.is_deleted]

    def purge_message(self, message_id):
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        del self._messages[message_id]

    @property
    def count(self):
        return sum(1 for m in self._messages.values() if not m.is_deleted)
