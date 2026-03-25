"""Step 1: Foundation — User, Channel, Message models + managers."""
import time
import pytest
from models import User, Channel, Message, UserStatus, ChannelType
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from exceptions import (
    UserNotFoundError,
    ChannelNotFoundError,
    MessageNotFoundError,
    DuplicateUserError,
    DuplicateChannelError,
)


class TestUserModel:
    def test_user_creation(self):
        u = User(username="alice", display_name="Alice", email="alice@example.com")
        assert u.username == "alice"
        assert u.display_name == "Alice"
        assert u.status == UserStatus.ONLINE
        assert u.metadata == {}

    def test_user_to_dict(self):
        u = User(username="bob")
        d = u.to_dict()
        assert d["username"] == "bob"
        assert d["status"] == "ONLINE"
        assert "id" in d

    def test_user_update(self):
        u = User(username="alice")
        old_ts = u.updated_at
        time.sleep(0.01)
        u.update(display_name="Alice W.")
        assert u.display_name == "Alice W."
        assert u.updated_at > old_ts

    def test_user_equality(self):
        u1 = User(id="same-id", username="a")
        u2 = User(id="same-id", username="b")
        assert u1 == u2

    def test_user_hash(self):
        u = User(id="u1", username="a")
        assert hash(u) == hash("u1")


class TestChannelModel:
    def test_channel_creation(self):
        ch = Channel(name="general", description="General chat")
        assert ch.name == "general"
        assert ch.channel_type == ChannelType.PUBLIC
        assert ch.metadata == {}

    def test_channel_to_dict(self):
        ch = Channel(name="dev", channel_type=ChannelType.PRIVATE)
        d = ch.to_dict()
        assert d["name"] == "dev"
        assert d["channel_type"] == "PRIVATE"

    def test_channel_update(self):
        ch = Channel(name="old")
        old_ts = ch.updated_at
        time.sleep(0.01)
        ch.update(name="new")
        assert ch.name == "new"
        assert ch.updated_at > old_ts


class TestMessageModel:
    def test_message_creation(self):
        m = Message(channel_id="ch1", sender_id="u1", content="Hello")
        assert m.content == "Hello"
        assert m.edited is False
        assert m.parent_id is None

    def test_message_edit(self):
        m = Message(content="old")
        old_ts = m.updated_at
        time.sleep(0.01)
        m.edit("new")
        assert m.content == "new"
        assert m.edited is True
        assert m.updated_at > old_ts

    def test_message_to_dict(self):
        m = Message(content="test")
        d = m.to_dict()
        assert d["content"] == "test"
        assert d["edited"] is False


class TestUserManager:
    def test_add_and_get_user(self):
        um = UserManager()
        user = um.add_user("alice", "Alice", "alice@test.com")
        fetched = um.get_user(user.id)
        assert fetched.username == "alice"

    def test_duplicate_username_raises(self):
        um = UserManager()
        um.add_user("alice")
        with pytest.raises(DuplicateUserError):
            um.add_user("alice")

    def test_duplicate_case_insensitive(self):
        um = UserManager()
        um.add_user("Alice")
        with pytest.raises(DuplicateUserError):
            um.add_user("alice")

    def test_get_user_not_found(self):
        um = UserManager()
        with pytest.raises(UserNotFoundError):
            um.get_user("nonexistent")

    def test_get_user_by_username(self):
        um = UserManager()
        user = um.add_user("Bob")
        found = um.get_user_by_username("bob")
        assert found.id == user.id

    def test_remove_user(self):
        um = UserManager()
        user = um.add_user("alice")
        um.remove_user(user.id)
        with pytest.raises(UserNotFoundError):
            um.get_user(user.id)

    def test_list_users_defensive(self):
        um = UserManager()
        um.add_user("a")
        um.add_user("b")
        lst = um.list_users()
        assert len(lst) == 2
        lst.clear()
        assert um.count == 2

    def test_set_status(self):
        um = UserManager()
        user = um.add_user("alice")
        um.set_status(user.id, UserStatus.AWAY)
        assert um.get_user(user.id).status == UserStatus.AWAY

    def test_search_users(self):
        um = UserManager()
        um.add_user("alice", display_name="Alice Wonderland")
        um.add_user("bob", display_name="Bob Builder")
        assert len(um.search_users("alice")) == 1
        assert len(um.search_users("ALICE")) == 1
        assert len(um.search_users("b")) == 1  # matches bob

    def test_count(self):
        um = UserManager()
        assert um.count == 0
        um.add_user("a")
        assert um.count == 1


class TestChannelManager:
    def test_create_and_get_channel(self):
        cm = ChannelManager()
        ch = cm.create_channel("general", "Main channel")
        fetched = cm.get_channel(ch.id)
        assert fetched.name == "general"

    def test_duplicate_channel_raises(self):
        cm = ChannelManager()
        cm.create_channel("general")
        with pytest.raises(DuplicateChannelError):
            cm.create_channel("General")

    def test_delete_channel(self):
        cm = ChannelManager()
        ch = cm.create_channel("tmp")
        cm.delete_channel(ch.id)
        with pytest.raises(ChannelNotFoundError):
            cm.get_channel(ch.id)

    def test_list_channels_defensive(self):
        cm = ChannelManager()
        cm.create_channel("a")
        cm.create_channel("b")
        lst = cm.list_channels()
        assert len(lst) == 2
        lst.clear()
        assert cm.count == 2

    def test_search_channels(self):
        cm = ChannelManager()
        cm.create_channel("general")
        cm.create_channel("random")
        results = cm.search_channels("gen")
        assert len(results) == 1

    def test_get_channels_by_type(self):
        cm = ChannelManager()
        cm.create_channel("pub", channel_type=ChannelType.PUBLIC)
        cm.create_channel("priv", channel_type=ChannelType.PRIVATE)
        pub = cm.get_channels_by_type(ChannelType.PUBLIC)
        assert len(pub) == 1

    def test_creator_is_member(self):
        cm = ChannelManager()
        ch = cm.create_channel("test", creator_id="u1")
        assert "u1" in ch.members


class TestMessageManager:
    def test_send_and_get_message(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "Hello world")
        fetched = mm.get_message(msg.id)
        assert fetched.content == "Hello world"

    def test_send_to_nonexistent_channel(self):
        cm = ChannelManager()
        mm = MessageManager(channel_manager=cm)
        with pytest.raises(ChannelNotFoundError):
            mm.send_message("bad-id", "u1", "Hello")

    def test_edit_message(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "original")
        edited = mm.edit_message(msg.id, "edited")
        assert edited.content == "edited"
        assert edited.edited is True

    def test_delete_message(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "delete me")
        mm.delete_message(msg.id)
        with pytest.raises(MessageNotFoundError):
            mm.get_message(msg.id)

    def test_get_messages_sorted(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        mm.send_message(ch.id, "u1", "first")
        time.sleep(0.01)
        mm.send_message(ch.id, "u1", "second")
        msgs = mm.get_messages(ch.id)
        assert msgs[0].content == "first"
        assert msgs[1].content == "second"

    def test_get_messages_by_user(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        mm.send_message(ch.id, "u1", "from u1")
        mm.send_message(ch.id, "u2", "from u2")
        u1_msgs = mm.get_messages_by_user("u1")
        assert len(u1_msgs) == 1

    def test_search_messages(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        mm.send_message(ch.id, "u1", "hello world")
        mm.send_message(ch.id, "u1", "goodbye world")
        mm.send_message(ch.id, "u1", "nothing here")
        results = mm.search_messages("world")
        assert len(results) == 2

    def test_search_case_insensitive(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        mm.send_message(ch.id, "u1", "Hello World")
        results = mm.search_messages("hello")
        assert len(results) == 1

    def test_count(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        assert mm.count == 0
        mm.send_message(ch.id, "u1", "msg1")
        assert mm.count == 1
