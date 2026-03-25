from models import AuditEntry


class AuditLogger:
    def __init__(self):
        self._entries = []

    def log(self, action, entity_type, entity_id, user_id=None, details=None):
        entry = AuditEntry(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details=details,
        )
        self._entries.append(entry)
        return entry

    def get_log(self):
        return list(self._entries)

    def get_log_by_entity(self, entity_type, entity_id):
        return [e for e in self._entries
                if e.entity_type == entity_type and e.entity_id == entity_id]

    def get_log_by_user(self, user_id):
        return [e for e in self._entries if e.user_id == user_id]

    def get_log_by_action(self, action):
        return [e for e in self._entries if e.action == action]

    def clear(self):
        self._entries = []
