"""Step 4: Message Threading."""
import time
import pytest
from models import ChannelType
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from thread_manager import ThreadManager
from notification import NotificationManager
from exceptions import MessageNotFoundError


def _setup():
    cm = ChannelManager()
    ch = cm.create_channel("general")
    mm = MessageManager(channel_manager=cm)
    tm = ThreadManager(message_manager=mm)
    return cm, ch, mm, tm


class TestThreading:
    def test_reply_creates_message(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root message")
        reply = tm.reply(root.id, ch.id, "u2", "Reply 1")
        assert reply.parent_id == root.id

    def test_get_thread(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply 1")
        tm.reply(root.id, ch.id, "u3", "Reply 2")
        thread = tm.get_thread(root.id)
        assert len(thread) == 2

    def test_get_thread_sorted(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "First reply")
        time.sleep(0.01)
        tm.reply(root.id, ch.id, "u3", "Second reply")
        thread = tm.get_thread(root.id)
        assert thread[0].content == "First reply"
        assert thread[1].content == "Second reply"

    def test_get_thread_count(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply 1")
        tm.reply(root.id, ch.id, "u3", "Reply 2")
        assert tm.get_thread_count(root.id) == 2

    def test_get_thread_participants(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply")
        tm.reply(root.id, ch.id, "u3", "Reply")
        participants = tm.get_thread_participants(root.id)
        assert participants == {"u1", "u2", "u3"}

    def test_root_only_in_get_messages(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply")
        messages = mm.get_messages(ch.id)
        assert len(messages) == 1
        assert messages[0].id == root.id

    def test_all_messages_includes_replies(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply")
        all_msgs = mm.get_all_messages(ch.id)
        assert len(all_msgs) == 2

    def test_search_includes_replies(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root message")
        tm.reply(root.id, ch.id, "u2", "Reply with keyword searchterm")
        results = mm.search_messages("searchterm")
        assert len(results) == 1

    def test_thread_count_property_on_root(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "R1")
        tm.reply(root.id, ch.id, "u3", "R2")
        # thread_count on the stored root message
        fetched_root = mm.get_message(root.id)
        assert fetched_root.thread_count == 2

    def test_reply_to_nonexistent_raises(self):
        cm, ch, mm, tm = _setup()
        with pytest.raises(MessageNotFoundError):
            tm.reply("bad-id", ch.id, "u1", "Reply")

    def test_reply_to_reply_threads_to_root(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        r1 = tm.reply(root.id, ch.id, "u2", "Reply 1")
        r2 = tm.reply(r1.id, ch.id, "u3", "Reply to reply")
        # Should thread under root, not under r1
        assert r2.parent_id == root.id

    def test_count_includes_replies(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply")
        assert mm.count == 2

    def test_thread_notifications(self):
        um = UserManager()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        u3 = um.add_user("charlie")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        nm = NotificationManager(user_manager=um)
        mm = MessageManager(channel_manager=cm)
        tm = ThreadManager(message_manager=mm, notification_manager=nm)
        root = mm.send_message(ch.id, u1.id, "Root")
        tm.reply(root.id, ch.id, u2.id, "Reply from bob")
        # u1 should be notified of reply
        u1_notifs = nm.get_notifications(u1.id)
        assert any(n.notification_type == "thread_reply" for n in u1_notifs)

    def test_thread_notification_excludes_sender(self):
        um = UserManager()
        u1 = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        nm = NotificationManager(user_manager=um)
        mm = MessageManager(channel_manager=cm)
        tm = ThreadManager(message_manager=mm, notification_manager=nm)
        root = mm.send_message(ch.id, u1.id, "Root")
        # u1 replies to own thread - should not notify self
        tm.reply(root.id, ch.id, u1.id, "Self reply")
        u1_notifs = nm.get_notifications(u1.id)
        assert len(u1_notifs) == 0

    def test_empty_thread(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        assert tm.get_thread(root.id) == []
        assert tm.get_thread_count(root.id) == 0

    def test_get_messages_by_user_includes_replies(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply from u2")
        u2_msgs = mm.get_messages_by_user("u2")
        assert len(u2_msgs) == 1

    def test_delete_reply_excluded_from_thread(self):
        cm, ch, mm, tm = _setup()
        root = mm.send_message(ch.id, "u1", "Root")
        r1 = tm.reply(root.id, ch.id, "u2", "Reply")
        mm.delete_message(r1.id)
        assert tm.get_thread_count(root.id) == 0

    def test_multiple_roots_independent_threads(self):
        cm, ch, mm, tm = _setup()
        root1 = mm.send_message(ch.id, "u1", "Root 1")
        root2 = mm.send_message(ch.id, "u1", "Root 2")
        tm.reply(root1.id, ch.id, "u2", "Reply to root 1")
        tm.reply(root2.id, ch.id, "u3", "Reply to root 2")
        assert tm.get_thread_count(root1.id) == 1
        assert tm.get_thread_count(root2.id) == 1
