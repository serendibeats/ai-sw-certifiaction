import re
from collections import defaultdict


class SearchIndex:
    def __init__(self):
        self._index = defaultdict(set)  # term -> set of message_ids
        self._message_terms = {}  # message_id -> set of terms
        self._indexed_messages = set()  # set of message_ids

    def _tokenize(self, content):
        # Split by whitespace -> lowercase -> remove punctuation
        tokens = content.split()
        tokens = [t.lower() for t in tokens]
        tokens = [re.sub(r'[^\w]', '', t) for t in tokens]
        tokens = [t for t in tokens if t]
        return tokens

    def index_message(self, message):
        terms = self._tokenize(message.content)
        term_set = set(terms)
        self._message_terms[message.id] = term_set
        self._indexed_messages.add(message.id)
        for term in term_set:
            self._index[term].add(message.id)

    def remove_message(self, message_id):
        if message_id in self._message_terms:
            for term in self._message_terms[message_id]:
                if term in self._index:
                    self._index[term].discard(message_id)
                    if not self._index[term]:
                        del self._index[term]
            del self._message_terms[message_id]
        self._indexed_messages.discard(message_id)

    def update_message(self, message):
        self.remove_message(message.id)
        self.index_message(message)

    def search(self, query, limit=50):
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scores = defaultdict(int)
        for term in query_terms:
            if term in self._index:
                for msg_id in self._index[term]:
                    scores[msg_id] += 1

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [msg_id for msg_id, _ in sorted_results[:limit]]

    def get_index_size(self):
        return len(self._indexed_messages)

    def get_unique_terms(self):
        return len(self._index)

    def get_top_terms(self, n=10):
        term_counts = [(term, len(msg_ids)) for term, msg_ids in self._index.items()]
        term_counts.sort(key=lambda x: x[1], reverse=True)
        return term_counts[:n]

    def rebuild(self, messages):
        self._index = defaultdict(set)
        self._message_terms = {}
        self._indexed_messages = set()
        for message in messages:
            self.index_message(message)
