"""Step 6: Full-Text Search Index."""
import time
import pytest
from models import Message
from channel_manager import ChannelManager
from message_manager import MessageManager
from thread_manager import ThreadManager
from search_index import SearchIndex


class TestSearchIndex:
    def test_index_and_search(self):
        si = SearchIndex()
        msg = Message(id="m1", content="hello world")
        si.index_message(msg)
        results = si.search("hello")
        assert "m1" in results

    def test_search_case_insensitive(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="Hello World"))
        results = si.search("hello")
        assert "m1" in results

    def test_remove_message(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello world"))
        si.remove_message("m1")
        results = si.search("hello")
        assert "m1" not in results

    def test_update_message(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello world"))
        si.update_message(Message(id="m1", content="goodbye world"))
        assert "m1" not in si.search("hello")
        assert "m1" in si.search("goodbye")

    def test_index_size(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello"))
        si.index_message(Message(id="m2", content="world"))
        assert si.get_index_size() == 2

    def test_rebuild(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="old data"))
        messages = [
            Message(id="m2", content="new data one"),
            Message(id="m3", content="new data two"),
        ]
        si.rebuild(messages)
        assert si.get_index_size() == 2
        assert "m1" not in si.search("old")
        assert "m2" in si.search("new")

    def test_search_scoring(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="python is great"))
        si.index_message(Message(id="m2", content="python programming python"))
        # m2 has python twice but set-based, so both match equally for single term
        results = si.search("python")
        assert "m1" in results and "m2" in results

    def test_multi_term_search_scoring(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="python is great"))
        si.index_message(Message(id="m2", content="python programming is fun"))
        # "python is" matches 2 terms in both
        results = si.search("python is")
        assert results[0] in ("m1", "m2")

    def test_search_limit(self):
        si = SearchIndex()
        for i in range(100):
            si.index_message(Message(id=f"m{i}", content="common word"))
        results = si.search("common", limit=10)
        assert len(results) == 10

    def test_search_empty_query(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello"))
        assert si.search("") == []

    def test_strip_punctuation(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello, world!"))
        results = si.search("hello")
        assert "m1" in results

    def test_unique_terms(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello world"))
        assert si.get_unique_terms() == 2

    def test_top_terms(self):
        si = SearchIndex()
        si.index_message(Message(id="m1", content="hello world"))
        si.index_message(Message(id="m2", content="hello python"))
        top = si.get_top_terms(1)
        assert top[0][0] == "hello"  # appears in 2 docs


class TestSearchIndexIntegration:
    def test_send_indexes_message(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        mm.send_message(ch.id, "u1", "indexed content")
        assert si.get_index_size() == 1
        results = si.search("indexed")
        assert len(results) == 1

    def test_edit_updates_index(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        msg = mm.send_message(ch.id, "u1", "original text")
        mm.edit_message(msg.id, "updated text")
        assert len(si.search("original")) == 0
        assert len(si.search("updated")) == 1

    def test_delete_removes_from_index(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        msg = mm.send_message(ch.id, "u1", "deletable content")
        mm.delete_message(msg.id)
        assert len(si.search("deletable")) == 0

    def test_search_via_manager_uses_index(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        mm.send_message(ch.id, "u1", "alpha bravo")
        mm.send_message(ch.id, "u1", "charlie delta")
        results = mm.search_messages("alpha")
        assert len(results) == 1

    def test_thread_reply_indexed(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        tm = ThreadManager(message_manager=mm)
        root = mm.send_message(ch.id, "u1", "root message")
        tm.reply(root.id, ch.id, "u2", "reply with uniqueword")
        results = si.search("uniqueword")
        assert len(results) == 1

    def test_search_excludes_deleted_via_index(self):
        si = SearchIndex()
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm, search_index=si)
        msg = mm.send_message(ch.id, "u1", "specialword content")
        mm.delete_message(msg.id)
        results = mm.search_messages("specialword")
        assert len(results) == 0

    def test_search_without_index_fallback(self):
        cm = ChannelManager()
        ch = cm.create_channel("general")
        mm = MessageManager(channel_manager=cm)  # no search_index
        mm.send_message(ch.id, "u1", "fallback search test")
        results = mm.search_messages("fallback")
        assert len(results) == 1
