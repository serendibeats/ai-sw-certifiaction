"""Step 3: Access Control — channel membership, permission checks."""
import pytest
from models import ChannelType
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from access_control import AccessController
from notification import NotificationManager
from mention import MentionParser
from exceptions import AccessDeniedError, ChannelNotFoundError


class TestAccessControlBasic:
    def test_join_public_channel(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general", channel_type=ChannelType.PUBLIC)
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u.id, ch.id)
        assert ac.is_member(u.id, ch.id)

    def test_join_private_channel_denied(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id="creator1")
        ac = AccessController(user_manager=um, channel_manager=cm)
        with pytest.raises(AccessDeniedError):
            ac.join_channel(u.id, ch.id)

    def test_invite_to_private_channel(self):
        um = UserManager()
        creator = um.add_user("creator")
        invitee = um.add_user("invitee")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id=creator.id)
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.invite_to_channel(creator.id, invitee.id, ch.id)
        assert ac.is_member(invitee.id, ch.id)

    def test_invite_by_non_member_denied(self):
        um = UserManager()
        outsider = um.add_user("outsider")
        invitee = um.add_user("invitee")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id="other")
        ac = AccessController(user_manager=um, channel_manager=cm)
        with pytest.raises(AccessDeniedError):
            ac.invite_to_channel(outsider.id, invitee.id, ch.id)

    def test_leave_channel(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u.id, ch.id)
        ac.leave_channel(u.id, ch.id)
        assert not ac.is_member(u.id, ch.id)

    def test_get_members_defensive(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u.id, ch.id)
        members = ac.get_members(ch.id)
        members.clear()
        assert ac.is_member(u.id, ch.id)

    def test_can_access_public(self):
        cm = ChannelManager()
        ch = cm.create_channel("general", channel_type=ChannelType.PUBLIC)
        ac = AccessController(channel_manager=cm)
        assert ac.can_access("any-user", ch.id) is True

    def test_can_access_private_member(self):
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id="u1")
        ac = AccessController(channel_manager=cm)
        assert ac.can_access("u1", ch.id) is True

    def test_can_access_private_non_member(self):
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id="u1")
        ac = AccessController(channel_manager=cm)
        assert ac.can_access("u2", ch.id) is False

    def test_creator_auto_member(self):
        cm = ChannelManager()
        ch = cm.create_channel("test", creator_id="u1")
        ac = AccessController(channel_manager=cm)
        assert ac.is_member("u1", ch.id)


class TestAccessControlOnMessages:
    def test_send_message_access_denied(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id="other")
        ac = AccessController(user_manager=um, channel_manager=cm)
        mm = MessageManager(channel_manager=cm, access_controller=ac)
        with pytest.raises(AccessDeniedError):
            mm.send_message(ch.id, u.id, "Hello")

    def test_send_message_access_granted(self):
        um = UserManager()
        creator = um.add_user("creator")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id=creator.id)
        ac = AccessController(user_manager=um, channel_manager=cm)
        mm = MessageManager(channel_manager=cm, access_controller=ac)
        msg = mm.send_message(ch.id, creator.id, "Hello")
        assert msg.content == "Hello"

    def test_public_channel_no_access_check(self):
        cm = ChannelManager()
        ch = cm.create_channel("general", channel_type=ChannelType.PUBLIC)
        ac = AccessController(channel_manager=cm)
        mm = MessageManager(channel_manager=cm, access_controller=ac)
        msg = mm.send_message(ch.id, "anyone", "Hello")
        assert msg.content == "Hello"

    def test_backward_compat_no_access_controller(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello")
        assert msg.content == "Hello"


class TestAccessControlOnNotifications:
    def test_all_mention_notifies_members_only(self):
        um = UserManager()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        u3 = um.add_user("charlie")
        cm = ChannelManager()
        ch = cm.create_channel("general", creator_id=u1.id)
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u2.id, ch.id)
        # u3 does NOT join
        nm = NotificationManager(user_manager=um, access_controller=ac)
        mp = MentionParser()
        mm = MessageManager(
            channel_manager=cm,
            mention_parser=mp,
            notification_manager=nm,
            access_controller=ac,
        )
        mm.send_message(ch.id, u1.id, "Hey @all look at this")
        # u2 should be notified (member, not sender)
        # u3 should NOT be notified (not a member)
        u2_notifs = nm.get_notifications(u2.id)
        u3_notifs = nm.get_notifications(u3.id)
        assert len(u2_notifs) >= 1
        assert len(u3_notifs) == 0

    def test_all_mention_excludes_sender(self):
        um = UserManager()
        u1 = um.add_user("alice")
        u2 = um.add_user("bob")
        cm = ChannelManager()
        ch = cm.create_channel("general", creator_id=u1.id)
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u2.id, ch.id)
        nm = NotificationManager(user_manager=um, access_controller=ac)
        mp = MentionParser()
        mm = MessageManager(
            channel_manager=cm,
            mention_parser=mp,
            notification_manager=nm,
            access_controller=ac,
        )
        mm.send_message(ch.id, u1.id, "@all important!")
        u1_notifs = nm.get_notifications(u1.id)
        assert len(u1_notifs) == 0

    def test_no_access_controller_skips_all_mention(self):
        um = UserManager()
        alice = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        nm = NotificationManager(user_manager=um)
        mp = MentionParser()
        mm = MessageManager(
            channel_manager=cm,
            mention_parser=mp,
            notification_manager=nm,
        )
        # Should not crash even without access_controller
        mm.send_message(ch.id, alice.id, "@all hello")

    def test_channel_membership_after_leave(self):
        um = UserManager()
        u = um.add_user("alice")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.join_channel(u.id, ch.id)
        assert ac.is_member(u.id, ch.id)
        ac.leave_channel(u.id, ch.id)
        assert not ac.is_member(u.id, ch.id)

    def test_nonexistent_channel_raises(self):
        ac = AccessController(channel_manager=ChannelManager())
        with pytest.raises(ChannelNotFoundError):
            ac.get_members("nonexistent")

    def test_invite_then_join_private(self):
        um = UserManager()
        creator = um.add_user("creator")
        invitee = um.add_user("invitee")
        cm = ChannelManager()
        ch = cm.create_channel("secret", channel_type=ChannelType.PRIVATE, creator_id=creator.id)
        ac = AccessController(user_manager=um, channel_manager=cm)
        ac.invite_to_channel(creator.id, invitee.id, ch.id)
        # Invitee is already a member after invite
        assert ac.is_member(invitee.id, ch.id)
        # Joining again should be fine (already member)
        ac.join_channel(invitee.id, ch.id)
        assert ac.is_member(invitee.id, ch.id)
