"""Step 2: Notification + Mention Parsing."""
import pytest
from models import UserStatus
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from notification import NotificationManager
from mention import MentionParser, MentionType


class TestMentionParser:
    def test_parse_single_user(self):
        mp = MentionParser()
        assert mp.parse("Hey @alice check this") == ["alice"]

    def test_parse_multiple_users(self):
        mp = MentionParser()
        result = mp.parse("@alice and @bob look at this")
        assert "alice" in result and "bob" in result

    def test_parse_no_mentions(self):
        mp = MentionParser()
        assert mp.parse("no mentions here") == []

    def test_parse_excludes_all_and_here(self):
        mp = MentionParser()
        assert mp.parse("@all please see @alice") == ["alice"]

    def test_parse_channel_mentions(self):
        mp = MentionParser()
        result = mp.parse_channel_mentions("check #general and #random")
        assert "general" in result and "random" in result

    def test_parse_all_mentions(self):
        mp = MentionParser()
        result = mp.parse_all_mentions("@all look at this")
        assert MentionType.ALL in result

    def test_parse_all_types(self):
        mp = MentionParser()
        result = mp.parse_all_types("@alice check #general @all")
        types = [t for t, _ in result]
        assert MentionType.USER in types
        assert MentionType.CHANNEL in types
        assert MentionType.ALL in types

    def test_parse_deduplicates(self):
        mp = MentionParser()
        result = mp.parse("@alice @alice @alice")
        assert result == ["alice"]


class TestNotificationManager:
    def test_notify_creates_notification(self):
        nm = NotificationManager()
        n = nm.notify("u1", "mention", "You were mentioned")
        assert n.user_id == "u1"
        assert n.notification_type == "mention"
        assert n.read is False

    def test_get_notifications(self):
        nm = NotificationManager()
        nm.notify("u1", "mention", "msg1")
        nm.notify("u1", "mention", "msg2")
        nm.notify("u2", "mention", "msg3")
        assert len(nm.get_notifications("u1")) == 2
        assert len(nm.get_notifications("u2")) == 1

    def test_get_unread_count(self):
        nm = NotificationManager()
        nm.notify("u1", "mention", "msg1")
        nm.notify("u1", "mention", "msg2")
        assert nm.get_unread_count("u1") == 2

    def test_mark_read(self):
        nm = NotificationManager()
        n = nm.notify("u1", "mention", "msg1")
        nm.mark_read(n.id)
        assert nm.get_unread_count("u1") == 0

    def test_mark_all_read(self):
        nm = NotificationManager()
        nm.notify("u1", "mention", "msg1")
        nm.notify("u1", "mention", "msg2")
        nm.mark_all_read("u1")
        assert nm.get_unread_count("u1") == 0

    def test_clear_notifications(self):
        nm = NotificationManager()
        nm.notify("u1", "mention", "msg1")
        nm.clear_notifications("u1")
        assert len(nm.get_notifications("u1")) == 0

    def test_mention_triggers_notification(self):
        um = UserManager()
        alice = um.add_user("alice")
        bob = um.add_user("bob")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        nm = NotificationManager(user_manager=um)
        mp = MentionParser()
        mm = MessageManager(
            channel_manager=cm,
            mention_parser=mp,
            notification_manager=nm,
        )
        mm.send_message(ch.id, bob.id, "Hey @alice check this out")
        notifs = nm.get_notifications(alice.id)
        assert len(notifs) >= 1
        assert notifs[0].notification_type == "mention"
