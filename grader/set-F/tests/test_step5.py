"""Step 5: Soft Delete + Rate Limiting."""
import time
import pytest
from models import ChannelType
from channel_manager import ChannelManager
from message_manager import MessageManager, RateLimiter
from thread_manager import ThreadManager
from exceptions import MessageNotFoundError, ChannelNotFoundError, RateLimitError


class TestSoftDeleteMessages:
    def test_deleted_message_not_in_get_messages(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        assert len(mm.get_messages(ch.id)) == 0

    def test_deleted_message_not_in_search(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "findable keyword")
        mm.delete_message(msg.id)
        assert len(mm.search_messages("findable")) == 0

    def test_deleted_message_raises_on_get(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        with pytest.raises(MessageNotFoundError):
            mm.get_message(msg.id)

    def test_get_deleted_messages(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        deleted = mm.get_deleted_messages(ch.id)
        assert len(deleted) == 1

    def test_deleted_message_has_timestamp(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        deleted = mm.get_deleted_messages(ch.id)
        assert deleted[0].deleted_at is not None

    def test_purge_message_hard_delete(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.purge_message(msg.id)
        assert len(mm.get_deleted_messages(ch.id)) == 0
        with pytest.raises(MessageNotFoundError):
            mm.purge_message(msg.id)

    def test_count_excludes_deleted(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        m1 = mm.send_message(ch.id, "u1", "msg1")
        mm.send_message(ch.id, "u1", "msg2")
        mm.delete_message(m1.id)
        assert mm.count == 1

    def test_get_messages_by_user_excludes_deleted(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        m1 = mm.send_message(ch.id, "u1", "msg1")
        mm.send_message(ch.id, "u1", "msg2")
        mm.delete_message(m1.id)
        assert len(mm.get_messages_by_user("u1")) == 1

    def test_get_all_messages_excludes_deleted(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        tm = ThreadManager(message_manager=mm)
        root = mm.send_message(ch.id, "u1", "Root")
        reply = tm.reply(root.id, ch.id, "u2", "Reply")
        mm.delete_message(reply.id)
        all_msgs = mm.get_all_messages(ch.id)
        assert len(all_msgs) == 1

    def test_double_delete_raises(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        with pytest.raises(MessageNotFoundError):
            mm.delete_message(msg.id)

    def test_edit_deleted_message_raises(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        mm.delete_message(msg.id)
        with pytest.raises(MessageNotFoundError):
            mm.edit_message(msg.id, "new content")


class TestSoftDeleteChannels:
    def test_deleted_channel_not_listed(self):
        cm = ChannelManager()
        ch = cm.create_channel("temp")
        cm.delete_channel(ch.id)
        assert len(cm.list_channels()) == 0

    def test_deleted_channel_raises_on_get(self):
        cm = ChannelManager()
        ch = cm.create_channel("temp")
        cm.delete_channel(ch.id)
        with pytest.raises(ChannelNotFoundError):
            cm.get_channel(ch.id)

    def test_get_deleted_channels(self):
        cm = ChannelManager()
        ch = cm.create_channel("temp")
        cm.delete_channel(ch.id)
        deleted = cm.get_deleted_channels()
        assert len(deleted) == 1

    def test_count_excludes_deleted(self):
        cm = ChannelManager()
        cm.create_channel("a")
        ch2 = cm.create_channel("b")
        cm.delete_channel(ch2.id)
        assert cm.count == 1

    def test_search_excludes_deleted(self):
        cm = ChannelManager()
        ch = cm.create_channel("searchable")
        cm.delete_channel(ch.id)
        assert len(cm.search_channels("search")) == 0

    def test_can_create_channel_with_deleted_name(self):
        cm = ChannelManager()
        ch = cm.create_channel("reusable")
        cm.delete_channel(ch.id)
        ch2 = cm.create_channel("reusable")
        assert ch2.name == "reusable"


class TestRateLimiter:
    def test_basic_rate_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=10.0)
        assert rl.check("u1") is True
        rl.record("u1")
        rl.record("u1")
        rl.record("u1")
        assert rl.check("u1") is False

    def test_remaining(self):
        rl = RateLimiter(max_requests=5, window_seconds=10.0)
        assert rl.get_remaining("u1") == 5
        rl.record("u1")
        assert rl.get_remaining("u1") == 4

    def test_separate_users(self):
        rl = RateLimiter(max_requests=2, window_seconds=10.0)
        rl.record("u1")
        rl.record("u1")
        assert rl.check("u1") is False
        assert rl.check("u2") is True

    def test_rate_limit_on_send_message(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        rl = RateLimiter(max_requests=2, window_seconds=10.0)
        mm = MessageManager(channel_manager=cm, rate_limiter=rl)
        mm.send_message(ch.id, "u1", "msg1")
        mm.send_message(ch.id, "u1", "msg2")
        with pytest.raises(RateLimitError):
            mm.send_message(ch.id, "u1", "msg3")

    def test_no_rate_limiter_no_limit(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        for i in range(100):
            mm.send_message(ch.id, "u1", f"msg{i}")
        assert mm.count == 100

    def test_window_expiry(self):
        rl = RateLimiter(max_requests=1, window_seconds=0.05)
        rl.record("u1")
        assert rl.check("u1") is False
        time.sleep(0.06)
        assert rl.check("u1") is True
