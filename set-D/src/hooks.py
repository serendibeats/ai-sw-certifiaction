import time

from exceptions import InvalidTaskError, InvalidProjectError, InvalidUserError


class HookContext:
    def __init__(self, action, entity_type, entity_id, data=None, user_id=None,
                 timestamp=None, result=None):
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.data = data if data is not None else {}
        self.user_id = user_id
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.result = result


class Hook:
    @property
    def name(self):
        return self.__class__.__name__

    def before(self, context):
        return context

    def after(self, context):
        return context


class AuditLogHook(Hook):
    def __init__(self):
        self._log = []

    def before(self, context):
        self._log.append({
            "phase": "before",
            "action": context.action,
            "entity_type": context.entity_type,
            "entity_id": context.entity_id,
            "data": context.data,
            "user_id": context.user_id,
            "timestamp": context.timestamp,
        })
        return context

    def after(self, context):
        self._log.append({
            "phase": "after",
            "action": context.action,
            "entity_type": context.entity_type,
            "entity_id": context.entity_id,
            "data": context.data,
            "user_id": context.user_id,
            "timestamp": context.timestamp,
            "result": context.result,
        })
        return context

    def get_audit_log(self):
        return list(self._log)

    def clear(self):
        self._log = []


class ValidationHook(Hook):
    def before(self, context):
        action = context.action
        data = context.data

        if action in ("create_task", "update_task"):
            if "title" in data and not data["title"]:
                raise InvalidTaskError("Title cannot be empty")

        if action in ("create_project", "update_project"):
            if "name" in data and not data["name"]:
                raise InvalidProjectError("Name cannot be empty")

        if action in ("create_user", "update_user"):
            if "username" in data and not data["username"]:
                raise InvalidUserError("Username cannot be empty")

        return context


class HookPipeline:
    def __init__(self):
        self._hooks = []

    def register(self, hook):
        self._hooks.append(hook)

    def unregister(self, hook_name):
        self._hooks = [h for h in self._hooks if h.name != hook_name]

    def execute_before(self, context):
        for hook in self._hooks:
            context = hook.before(context)
        return context

    def execute_after(self, context):
        for hook in self._hooks:
            context = hook.after(context)
        return context

    def get_hooks(self):
        return [h.name for h in self._hooks]
