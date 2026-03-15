"""Step 8: Message Validation + Channel Stats + Reports."""
import time
import pytest
from models import ChannelType
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from search_index import SearchIndex
from reports import ReportGenerator
from exceptions import InvalidMessageError


class TestMessageValidation:
    def test_empty_content_rejected(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        with pytest.raises(InvalidMessageError):
            mm.send_message(ch.id, "u1", "")

    def test_whitespace_only_rejected(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        with pytest.raises(InvalidMessageError):
            mm.send_message(ch.id, "u1", "   ")

    def test_max_length_rejected(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        with pytest.raises(InvalidMessageError):
            mm.send_message(ch.id, "u1", "x" * 10001)

    def test_max_length_boundary_ok(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "x" * 10000)
        assert len(msg.content) == 10000

    def test_forbidden_words_warning(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, forbidden_words=["spam", "ads"])
        msg = mm.send_message(ch.id, "u1", "Check out this spam content")
        assert "warnings" in msg.metadata

    def test_forbidden_words_dont_block(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, forbidden_words=["badword"])
        msg = mm.send_message(ch.id, "u1", "This has a badword in it")
        assert msg.content == "This has a badword in it"

    def test_edit_validates_too(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Valid")
        with pytest.raises(InvalidMessageError):
            mm.edit_message(msg.id, "")

    def test_normal_message_no_warnings(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, forbidden_words=["badword"])
        msg = mm.send_message(ch.id, "u1", "Clean message")
        assert "warnings" not in msg.metadata


class TestChannelStats:
    def test_channel_stats_basic(self):
        cm = ChannelManager()
        ch = cm.create_channel("general", creator_id="u1")
        mm = MessageManager(channel_manager=cm)
        cm._message_manager = mm
        mm.send_message(ch.id, "u1", "msg1")
        mm.send_message(ch.id, "u1", "msg2")
        stats = cm.get_channel_stats(ch.id)
        assert stats["message_count"] == 2
        assert stats["member_count"] == 1
        assert "u1" in stats["active_users"]

    def test_channel_stats_last_activity(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        cm._message_manager = mm
        msg = mm.send_message(ch.id, "u1", "msg")
        stats = cm.get_channel_stats(ch.id)
        assert stats["last_activity"] is not None

    def test_channel_stats_empty(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        cm._message_manager = mm
        stats = cm.get_channel_stats(ch.id)
        assert stats["message_count"] == 0
        assert stats["last_activity"] is None

    def test_channel_stats_no_message_manager(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        stats = cm.get_channel_stats(ch.id)
        assert stats["message_count"] == 0

    def test_channel_stats_multiple_users(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        cm._message_manager = mm
        mm.send_message(ch.id, "u1", "from u1")
        mm.send_message(ch.id, "u2", "from u2")
        stats = cm.get_channel_stats(ch.id)
        assert len(stats["active_users"]) == 2


class TestReports:
    def _setup(self):
        um = UserManager()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        cm = ChannelManager()
        ch = cm.create_channel("general", creator_id=u1.id)
        si = SearchIndex()
        mm = MessageManager(channel_manager=cm, search_index=si)
        cm._message_manager = mm
        return um, u1, u2, cm, ch, mm, si

    def test_channel_activity_report(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        mm.send_message(ch.id, u1.id, "msg1")
        mm.send_message(ch.id, u2.id, "msg2")
        rg = ReportGenerator(channel_manager=cm, message_manager=mm)
        report = rg.channel_activity_report(ch.id)
        assert report["total_messages"] == 2
        assert len(report["top_posters"]) == 2

    def test_user_activity_report(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        mm.send_message(ch.id, u1.id, "Hello world")
        mm.send_message(ch.id, u1.id, "Another message")
        rg = ReportGenerator(message_manager=mm, user_manager=um)
        report = rg.user_activity_report(u1.id)
        assert report["messages_sent"] == 2
        assert report["avg_message_length"] > 0

    def test_search_index_report(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        mm.send_message(ch.id, u1.id, "hello world")
        mm.send_message(ch.id, u1.id, "hello python")
        rg = ReportGenerator(search_index=si)
        report = rg.search_index_report()
        assert report["total_indexed"] == 2
        assert report["unique_terms"] > 0

    def test_system_report(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        mm.send_message(ch.id, u1.id, "msg")
        rg = ReportGenerator(
            channel_manager=cm, message_manager=mm, user_manager=um
        )
        report = rg.system_report()
        assert report["total_users"] == 2
        assert report["total_channels"] == 1
        assert report["total_messages"] == 1

    def test_system_report_active_channels(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        ch2 = cm.create_channel("empty-channel")
        mm.send_message(ch.id, u1.id, "msg")
        rg = ReportGenerator(channel_manager=cm, message_manager=mm)
        report = rg.system_report()
        assert report["active_channels"] == 1

    def test_empty_reports(self):
        rg = ReportGenerator()
        assert rg.system_report()["total_users"] == 0
        assert rg.channel_activity_report("ch1")["total_messages"] == 0
        assert rg.user_activity_report("u1")["messages_sent"] == 0
        assert rg.search_index_report()["total_indexed"] == 0

    def test_channel_report_messages_per_day(self):
        um, u1, u2, cm, ch, mm, si = self._setup()
        mm.send_message(ch.id, u1.id, "msg1")
        time.sleep(0.01)
        mm.send_message(ch.id, u1.id, "msg2")
        rg = ReportGenerator(channel_manager=cm, message_manager=mm)
        report = rg.channel_activity_report(ch.id)
        assert report["messages_per_day"] > 0
