"""Step 7: Encryption + Audit Log."""
import time
import pytest
from models import Message
from user_manager import UserManager
from channel_manager import ChannelManager
from message_manager import MessageManager
from thread_manager import ThreadManager
from search_index import SearchIndex
from encryption import EncryptionManager
from audit import AuditLogger
from exceptions import EncryptionError


class TestEncryptionManager:
    def test_encrypt_decrypt_roundtrip(self):
        em = EncryptionManager(key="secretkey")
        plaintext = "Hello, World!"
        ciphertext = em.encrypt(plaintext)
        assert ciphertext != plaintext
        assert em.decrypt(ciphertext) == plaintext

    def test_encrypted_has_prefix(self):
        em = EncryptionManager(key="mykey")
        ct = em.encrypt("test")
        assert ct.startswith("ENC:")

    def test_is_encrypted(self):
        em = EncryptionManager(key="mykey")
        assert em.is_encrypted("ENC:abc") is True
        assert em.is_encrypted("plain text") is False
        assert em.is_encrypted(None) is False

    def test_decrypt_plaintext_passthrough(self):
        em = EncryptionManager(key="mykey")
        assert em.decrypt("plain text") == "plain text"

    def test_empty_string_passthrough(self):
        em = EncryptionManager(key="mykey")
        assert em.encrypt("") == ""

    def test_empty_key_raises(self):
        with pytest.raises(EncryptionError):
            EncryptionManager(key="")

    def test_unicode_content(self):
        em = EncryptionManager(key="key123")
        text = "Hello unicode chars"
        assert em.decrypt(em.encrypt(text)) == text

    def test_long_content(self):
        em = EncryptionManager(key="k")
        text = "x" * 5000
        assert em.decrypt(em.encrypt(text)) == text


class TestEncryptionIntegration:
    def test_messages_stored_encrypted(self):
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, encryption_manager=em)
        msg = mm.send_message(ch.id, "u1", "Secret message")
        # The returned message should be decrypted
        assert msg.content == "Secret message"
        # But stored content is encrypted
        stored = mm._messages[msg.id]
        assert stored.content.startswith("ENC:")

    def test_get_message_decrypts(self):
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, encryption_manager=em)
        msg = mm.send_message(ch.id, "u1", "Secret")
        fetched = mm.get_message(msg.id)
        assert fetched.content == "Secret"

    def test_get_messages_decrypts_all(self):
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, encryption_manager=em)
        mm.send_message(ch.id, "u1", "Message 1")
        mm.send_message(ch.id, "u1", "Message 2")
        messages = mm.get_messages(ch.id)
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Message 2"

    def test_edit_encrypts_new_content(self):
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, encryption_manager=em)
        msg = mm.send_message(ch.id, "u1", "Original")
        edited = mm.edit_message(msg.id, "Edited")
        assert edited.content == "Edited"
        stored = mm._messages[msg.id]
        assert stored.content.startswith("ENC:")

    def test_search_on_encrypted_messages(self):
        em = EncryptionManager(key="secret")
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(
            channel_manager=cm, encryption_manager=em, search_index=si
        )
        mm.send_message(ch.id, "u1", "searchable encrypted content")
        results = mm.search_messages("searchable")
        assert len(results) == 1
        assert results[0].content == "searchable encrypted content"

    def test_search_fallback_on_encrypted_no_index(self):
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, encryption_manager=em)
        mm.send_message(ch.id, "u1", "findme content")
        results = mm.search_messages("findme")
        assert len(results) == 1

    def test_mixed_plain_and_encrypted(self):
        """Messages without ENC: prefix treated as plaintext."""
        em = EncryptionManager(key="secret")
        cm = ChannelManager()
        ch = cm.create_channel("general")
        # First send without encryption
        mm_plain = MessageManager(channel_manager=cm)
        plain_msg = mm_plain.send_message(ch.id, "u1", "plain message")
        # Now create a new manager with encryption that uses same storage
        mm_enc = MessageManager(channel_manager=cm, encryption_manager=em)
        mm_enc._messages = mm_plain._messages  # share storage
        enc_msg = mm_enc.send_message(ch.id, "u1", "encrypted message")
        # Both should be readable
        fetched_plain = mm_enc.get_message(plain_msg.id)
        fetched_enc = mm_enc.get_message(enc_msg.id)
        assert fetched_plain.content == "plain message"
        assert fetched_enc.content == "encrypted message"

    def test_backward_compat_no_encryption(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)
        msg = mm.send_message(ch.id, "u1", "No encryption")
        assert mm.get_message(msg.id).content == "No encryption"

    def test_thread_reply_encrypted(self):
        em = EncryptionManager(key="secret")
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(
            channel_manager=cm, encryption_manager=em, search_index=si
        )
        tm = ThreadManager(message_manager=mm)
        root = mm.send_message(ch.id, "u1", "Root encrypted")
        reply = tm.reply(root.id, ch.id, "u2", "Reply encrypted uniqueterm")
        # Reply should be decrypted in return
        assert reply.content == "Reply encrypted uniqueterm"
        # Stored encrypted
        assert mm._messages[reply.id].content.startswith("ENC:")
        # Searchable
        results = mm.search_messages("uniqueterm")
        assert len(results) == 1


class TestAuditLogger:
    def test_log_entry(self):
        al = AuditLogger()
        entry = al.log("create", "channel", "ch1", user_id="u1")
        assert entry.action == "create"
        assert entry.entity_type == "channel"

    def test_get_log_defensive(self):
        al = AuditLogger()
        al.log("a", "b", "c")
        log = al.get_log()
        log.clear()
        assert len(al.get_log()) == 1

    def test_get_by_entity(self):
        al = AuditLogger()
        al.log("create", "channel", "ch1")
        al.log("update", "channel", "ch1")
        al.log("create", "message", "m1")
        results = al.get_log_by_entity("channel", "ch1")
        assert len(results) == 2

    def test_get_by_user(self):
        al = AuditLogger()
        al.log("send", "message", "m1", user_id="u1")
        al.log("send", "message", "m2", user_id="u2")
        results = al.get_log_by_user("u1")
        assert len(results) == 1

    def test_get_by_action(self):
        al = AuditLogger()
        al.log("send", "message", "m1")
        al.log("edit", "message", "m2")
        al.log("send", "message", "m3")
        results = al.get_log_by_action("send")
        assert len(results) == 2

    def test_clear(self):
        al = AuditLogger()
        al.log("a", "b", "c")
        al.clear()
        assert len(al.get_log()) == 0


class TestAuditIntegration:
    def test_send_message_audited(self):
        al = AuditLogger()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, audit_logger=al)
        mm.send_message(ch.id, "u1", "Hello")
        entries = al.get_log_by_action("send_message")
        assert len(entries) == 1

    def test_edit_message_audited(self):
        al = AuditLogger()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, audit_logger=al)
        msg = mm.send_message(ch.id, "u1", "Original")
        mm.edit_message(msg.id, "Edited")
        entries = al.get_log_by_action("edit_message")
        assert len(entries) == 1

    def test_delete_message_audited(self):
        al = AuditLogger()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, audit_logger=al)
        msg = mm.send_message(ch.id, "u1", "Delete me")
        mm.delete_message(msg.id)
        entries = al.get_log_by_action("delete_message")
        assert len(entries) == 1

    def test_channel_operations_audited(self):
        al = AuditLogger()
        cm = ChannelManager(audit_logger=al)
        ch = cm.create_channel("general")
        cm.update_channel(ch.id, description="Updated")
        cm.delete_channel(ch.id)
        assert len(al.get_log_by_action("create_channel")) == 1
        assert len(al.get_log_by_action("update_channel")) == 1
        assert len(al.get_log_by_action("delete_channel")) == 1

    def test_thread_reply_audited(self):
        al = AuditLogger()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, audit_logger=al)
        tm = ThreadManager(message_manager=mm)
        root = mm.send_message(ch.id, "u1", "Root")
        tm.reply(root.id, ch.id, "u2", "Reply")
        entries = al.get_log_by_action("thread_reply")
        assert len(entries) == 1
