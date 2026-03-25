import copy
from models import Message
from exceptions import MessageNotFoundError


class ThreadManager:
    def __init__(self, message_manager=None, notification_manager=None):
        self._message_manager = message_manager
        self._notification_manager = notification_manager
        self._threads = {}  # root_message_id -> [reply_id, ...]

    def reply(self, parent_id, channel_id, sender_id, content):
        parent_msg = self._message_manager.get_message(parent_id)

        # Find root message (flatten nested replies)
        root_id = parent_id
        if parent_msg.parent_id is not None:
            root_id = parent_msg.parent_id

        plaintext = content
        stored_content = content
        if self._message_manager._encryption_manager is not None:
            stored_content = self._message_manager._encryption_manager.encrypt(content)

        # Create the reply message
        message = Message(
            channel_id=channel_id,
            sender_id=sender_id,
            content=stored_content,
            parent_id=root_id,
        )
        self._message_manager._messages[message.id] = message

        # Index reply in search index with plaintext
        if self._message_manager._search_index is not None:
            index_msg = copy.copy(message)
            index_msg.content = plaintext
            self._message_manager._search_index.index_message(index_msg)

        # Track in threads
        if root_id not in self._threads:
            self._threads[root_id] = []
        self._threads[root_id].append(message.id)

        # Increment root message thread_count
        # Access the raw message to update thread_count (not decrypted copy)
        raw_root = self._message_manager._messages[root_id]
        raw_root.thread_count += 1

        # Audit log
        if self._message_manager._audit_logger is not None:
            self._message_manager._audit_logger.log(
                "thread_reply", "message", message.id,
                user_id=sender_id)

        # Notify thread participants (excluding sender)
        if self._notification_manager is not None:
            participants = self.get_thread_participants(root_id)
            for participant_id in participants:
                if participant_id != sender_id:
                    self._notification_manager.notify(
                        participant_id, "thread_reply", plaintext, source_id=message.id
                    )

        # Return decrypted message
        return self._message_manager._decrypt_message(message)

    def get_thread(self, message_id):
        if message_id not in self._threads:
            return []
        replies = []
        for rid in self._threads[message_id]:
            if rid in self._message_manager._messages:
                msg = self._message_manager._messages[rid]
                if not msg.is_deleted:
                    replies.append(self._message_manager._decrypt_message(msg))
        return sorted(replies, key=lambda m: m.created_at)

    def get_thread_count(self, message_id):
        if message_id not in self._threads:
            return 0
        count = 0
        for rid in self._threads[message_id]:
            if rid in self._message_manager._messages:
                msg = self._message_manager._messages[rid]
                if not msg.is_deleted:
                    count += 1
        return count

    def get_thread_participants(self, message_id):
        participants = set()
        # Include root message sender
        try:
            root_msg = self._message_manager.get_message(message_id)
            participants.add(root_msg.sender_id)
        except Exception:
            pass
        # Include all reply senders
        for reply in self.get_thread(message_id):
            participants.add(reply.sender_id)
        return participants
