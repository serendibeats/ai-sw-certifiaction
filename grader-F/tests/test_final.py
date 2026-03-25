"""Final integration tests -- NOT shown to AI during development.

Tests cross-step interactions across all 8 steps.
Each test targets a specific spaghetti pattern from sequential development.
"""
import time
import pytest
from models import User, Channel, Message, UserStatus, ChannelType, Notification
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager, RateLimiter
from notification import NotificationManager
from mention import MentionParser, MentionType
from access_control import AccessController
from thread_manager import ThreadManager
from search_index import SearchIndex
from encryption import EncryptionManager
from audit import AuditLogger
from reports import ReportGenerator
from exceptions import (
    UserNotFoundError,
    ChannelNotFoundError,
    MessageNotFoundError,
    DuplicateUserError,
    DuplicateChannelError,
    InvalidMessageError,
    AccessDeniedError,
    RateLimitError,
)


def _full_setup():
    """Full system setup with all components wired together."""
    um = UserManager()
    al = AuditLogger()
    cm = ChannelManager(audit_logger=al)
    si = SearchIndex()
    em = EncryptionManager(key="test-secret-key-2024")
    nm = NotificationManager(user_manager=um)
    mp = MentionParser()
    ac = AccessController(user_manager=um, channel_manager=cm)
    rl = RateLimiter(max_requests=100, window_seconds=60.0)
    mm = MessageManager(
        channel_manager=cm,
        mention_parser=mp,
        notification_manager=nm,
        access_controller=ac,
        rate_limiter=rl,
        search_index=si,
        encryption_manager=em,
        audit_logger=al,
    )
    nm._access_controller = ac
    cm._message_manager = mm
    tm = ThreadManager(message_manager=mm, notification_manager=nm)
    rg = ReportGenerator(
        channel_manager=cm, message_manager=mm,
        user_manager=um, search_index=si,
    )
    return um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg


# --- E2E Full Pipeline ---

class TestEndToEndPipeline:
    def test_full_flow(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        # Create users
        alice = um.add_user("alice", "Alice W.")
        bob = um.add_user("bob", "Bob B.")
        charlie = um.add_user("charlie", "Charlie C.")
        # Create channel
        ch = cm.create_channel("general", "General chat", creator_id=alice.id)
        ac.join_channel(bob.id, ch.id)
        ac.join_channel(charlie.id, ch.id)
        # Send messages
        m1 = mm.send_message(ch.id, alice.id, "Hello everyone!")
        m2 = mm.send_message(ch.id, bob.id, "Hey @alice, check this out")
        # Alice should get mention notification
        alice_notifs = nm.get_notifications(alice.id)
        assert any(n.notification_type == "mention" for n in alice_notifs)
        # Thread reply
        r1 = tm.reply(m1.id, ch.id, bob.id, "Great thread!")
        r2 = tm.reply(m1.id, ch.id, charlie.id, "Agreed!")
        # alice should get thread notification
        alice_thread_notifs = [
            n for n in nm.get_notifications(alice.id)
            if n.notification_type == "thread_reply"
        ]
        assert len(alice_thread_notifs) >= 1
        # Search
        results = mm.search_messages("thread")
        assert len(results) >= 1
        # Reports
        sys_report = rg.system_report()
        assert sys_report["total_users"] == 3
        assert sys_report["total_messages"] >= 4

    def test_full_flow_with_all_mention(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        alice = um.add_user("alice")
        bob = um.add_user("bob")
        ch = cm.create_channel("general", creator_id=alice.id)
        ac.join_channel(bob.id, ch.id)
        mm.send_message(ch.id, alice.id, "Hey @all important update!")
        bob_notifs = nm.get_notifications(bob.id)
        assert any(n.notification_type == "mention_all" for n in bob_notifs)
        alice_notifs = nm.get_notifications(alice.id)
        # alice is sender, should not get @all notification
        assert not any(n.notification_type == "mention_all" for n in alice_notifs)


# --- Access Control Across Operations ---

class TestAccessControlIntegration:
    def test_private_channel_full_flow(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        creator = um.add_user("creator")
        member = um.add_user("member")
        outsider = um.add_user("outsider")
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id=creator.id)
        ac.invite_to_channel(creator.id, member.id, ch.id)
        # Creator and member can send
        mm.send_message(ch.id, creator.id, "Secret msg 1")
        mm.send_message(ch.id, member.id, "Secret msg 2")
        # Outsider cannot
        with pytest.raises(AccessDeniedError):
            mm.send_message(ch.id, outsider.id, "Denied!")
        # Messages are readable by members
        msgs = mm.get_messages(ch.id)
        assert len(msgs) == 2

    def test_leave_then_denied(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        ch = cm.create_channel("private-ch", channel_type=ChannelType.PRIVATE, creator_id=u1.id)
        ac.invite_to_channel(u1.id, u2.id, ch.id)
        mm.send_message(ch.id, u2.id, "I'm in!")
        ac.leave_channel(u2.id, ch.id)
        with pytest.raises(AccessDeniedError):
            mm.send_message(ch.id, u2.id, "Can I still post?")

    def test_public_channel_no_membership_required(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("open", channel_type=ChannelType.PUBLIC)
        msg = mm.send_message(ch.id, u.id, "Anyone can post")
        assert msg.content == "Anyone can post"


# --- Soft Delete Consistency ---

class TestSoftDeleteConsistency:
    def test_deleted_messages_excluded_from_search(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "uniquesearchword here")
        mm.delete_message(msg.id)
        results = mm.search_messages("uniquesearchword")
        assert len(results) == 0

    def test_deleted_messages_excluded_from_threads(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        ch = cm.create_channel("general", creator_id=u1.id)
        ac.join_channel(u2.id, ch.id)
        root = mm.send_message(ch.id, u1.id, "Root")
        reply = tm.reply(root.id, ch.id, u2.id, "Reply")
        mm.delete_message(reply.id)
        assert tm.get_thread_count(root.id) == 0

    def test_deleted_channel_hides_messages(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("temp", creator_id=u.id)
        mm.send_message(ch.id, u.id, "msg in temp")
        cm.delete_channel(ch.id)
        with pytest.raises(ChannelNotFoundError):
            mm.get_messages(ch.id)

    def test_soft_delete_preserves_count_accuracy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        m1 = mm.send_message(ch.id, u.id, "msg1")
        mm.send_message(ch.id, u.id, "msg2")
        mm.delete_message(m1.id)
        assert mm.count == 1

    def test_get_deleted_messages(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "delete me")
        mm.delete_message(msg.id)
        deleted = mm.get_deleted_messages(ch.id)
        assert len(deleted) == 1


# --- Encryption + Search Integration ---

class TestEncryptionSearchIntegration:
    def test_encrypted_messages_searchable(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        mm.send_message(ch.id, u.id, "encrypted secret payload")
        results = mm.search_messages("payload")
        assert len(results) == 1
        assert results[0].content == "encrypted secret payload"

    def test_encrypted_edit_updates_index(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "before edit oldword")
        mm.edit_message(msg.id, "after edit newword")
        assert len(mm.search_messages("oldword")) == 0
        assert len(mm.search_messages("newword")) == 1

    def test_encrypted_delete_removes_from_index(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "indexedword content")
        mm.delete_message(msg.id)
        assert len(si.search("indexedword")) == 0

    def test_thread_encrypted_and_searchable(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        ch = cm.create_channel("general", creator_id=u1.id)
        ac.join_channel(u2.id, ch.id)
        root = mm.send_message(ch.id, u1.id, "Root msg")
        reply = tm.reply(root.id, ch.id, u2.id, "Reply with threadkeyword")
        results = mm.search_messages("threadkeyword")
        assert len(results) == 1


# --- Audit Trail Completeness ---

class TestAuditTrailCompleteness:
    def test_full_audit_trail(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "Hello")
        mm.edit_message(msg.id, "Hello edited")
        mm.delete_message(msg.id)
        log = al.get_log()
        actions = [e.action for e in log]
        assert "create_channel" in actions
        assert "send_message" in actions
        assert "edit_message" in actions
        assert "delete_message" in actions

    def test_thread_reply_audited(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        ch = cm.create_channel("general", creator_id=u1.id)
        ac.join_channel(u2.id, ch.id)
        root = mm.send_message(ch.id, u1.id, "Root")
        tm.reply(root.id, ch.id, u2.id, "Reply")
        entries = al.get_log_by_action("thread_reply")
        assert len(entries) >= 1


# --- Rate Limiting ---

class TestRateLimitingIntegration:
    def test_rate_limit_across_channels(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        rl_strict = RateLimiter(max_requests=2, window_seconds=60.0)
        mm._rate_limiter = rl_strict
        u = um.add_user("alice")
        ch1 = cm.create_channel("ch1", creator_id=u.id)
        ch2 = cm.create_channel("ch2", creator_id=u.id)
        mm.send_message(ch1.id, u.id, "msg1")
        mm.send_message(ch2.id, u.id, "msg2")
        with pytest.raises(RateLimitError):
            mm.send_message(ch1.id, u.id, "msg3")

    def test_rate_limit_per_user(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        rl_strict = RateLimiter(max_requests=1, window_seconds=60.0)
        mm._rate_limiter = rl_strict
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        ch = cm.create_channel("general", creator_id=u1.id)
        ac.join_channel(u2.id, ch.id)
        mm.send_message(ch.id, u1.id, "msg1")
        mm.send_message(ch.id, u2.id, "msg2")  # different user, OK
        with pytest.raises(RateLimitError):
            mm.send_message(ch.id, u1.id, "msg3")  # u1 limited

    def test_no_rate_limiter_backward_compat(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        for i in range(50):
            mm.send_message(ch.id, "u1", f"msg{i}")
        assert mm.count == 50


# --- Case Insensitivity ---

class TestCaseInsensitivity:
    def test_user_search_case_insensitive(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        um.add_user("Alice", "Alice Wonderland")
        results = um.search_users("ALICE")
        assert len(results) == 1

    def test_channel_search_case_insensitive(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        cm.create_channel("General")
        results = cm.search_channels("general")
        assert len(results) == 1

    def test_message_search_case_insensitive(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        mm.send_message(ch.id, u.id, "Hello World")
        results = mm.search_messages("hello")
        assert len(results) == 1

    def test_get_user_by_username_case_insensitive(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        user = um.add_user("Bob")
        found = um.get_user_by_username("BOB")
        assert found.id == user.id

    def test_duplicate_channel_name_case_insensitive(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        cm.create_channel("Test")
        with pytest.raises(DuplicateChannelError):
            cm.create_channel("test")


# --- Defensive Copies ---

class TestDefensiveCopies:
    def test_list_users_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        um.add_user("alice")
        um.list_users().clear()
        assert um.count == 1

    def test_list_channels_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        cm.create_channel("general")
        cm.list_channels().clear()
        assert cm.count == 1

    def test_get_members_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general")
        ac.join_channel(u.id, ch.id)
        ac.get_members(ch.id).clear()
        assert ac.is_member(u.id, ch.id)

    def test_get_notifications_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        nm.notify("u1", "test", "test msg")
        nm.get_notifications("u1").clear()
        assert len(nm.get_notifications("u1")) == 1

    def test_audit_log_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        al.log("test", "entity", "e1")
        al.get_log().clear()
        assert len(al.get_log()) == 1

    def test_search_users_copy(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        um.add_user("alice")
        um.search_users("alice").clear()
        assert len(um.search_users("alice")) == 1


# --- Backward Compatibility ---

class TestBackwardCompat:
    def test_message_manager_no_optional_deps(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Simple message")
        assert msg.content == "Simple message"

    def test_message_manager_minimal_setup(self):
        mm = MessageManager()
        # Without channel_manager, send_message should still work
        msg = mm.send_message("ch1", "u1", "No channel check")
        assert msg.content == "No channel check"

    def test_channel_manager_no_audit(self):
        cm = ChannelManager()
        ch = cm.create_channel("test")
        assert ch.name == "test"

    def test_notification_manager_standalone(self):
        nm = NotificationManager()
        n = nm.notify("u1", "test", "content")
        assert n.notification_type == "test"

    def test_search_index_standalone(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="standalone test"))
        assert len(si.search("standalone")) == 1


# --- Complex Integration ---

class TestComplexIntegration:
    def test_mention_in_thread_reply(self):
        """Mentions in thread replies should still trigger notifications."""
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        alice = um.add_user("alice")
        bob = um.add_user("bob")
        charlie = um.add_user("charlie")
        ch = cm.create_channel("general", creator_id=alice.id)
        ac.join_channel(bob.id, ch.id)
        ac.join_channel(charlie.id, ch.id)
        root = mm.send_message(ch.id, alice.id, "Start discussion")
        # Bob's reply mentions charlie -- ThreadManager.reply doesn't
        # directly call mention parsing (only send_message does),
        # but thread notifications should still fire
        tm.reply(root.id, ch.id, bob.id, "Hey check this out")
        # Alice should get thread_reply notification
        alice_notifs = nm.get_notifications(alice.id)
        assert any(n.notification_type == "thread_reply" for n in alice_notifs)

    def test_channel_stats_with_threads_and_deletes(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        m1 = mm.send_message(ch.id, u.id, "Root 1")
        m2 = mm.send_message(ch.id, u.id, "Root 2")
        tm.reply(m1.id, ch.id, u.id, "Reply to root 1")
        mm.delete_message(m2.id)
        # Stats should show root-only messages (non-deleted)
        stats = cm.get_channel_stats(ch.id)
        assert stats["message_count"] == 1  # only m1 (root, non-deleted)

    def test_report_with_encrypted_messages(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        mm.send_message(ch.id, u.id, "Hello world encrypted")
        report = rg.user_activity_report(u.id)
        assert report["messages_sent"] == 1
        # avg_message_length should be based on decrypted content
        assert report["avg_message_length"] > 0

    def test_purge_after_soft_delete(self):
        um, cm, mm, tm, nm, mp, ac, rl, si, em, al, rg = _full_setup()
        u = um.add_user("alice")
        ch = cm.create_channel("general", creator_id=u.id)
        msg = mm.send_message(ch.id, u.id, "purge me")
        mm.delete_message(msg.id)
        # soft-deleted, now purge
        mm.purge_message(msg.id)
        assert len(mm.get_deleted_messages(ch.id)) == 0
