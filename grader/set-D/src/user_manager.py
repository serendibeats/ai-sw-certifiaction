import uuid

from models import User
from exceptions import UserNotFoundError, InvalidUserError
from hooks import HookContext


class UserManager:
    def __init__(self, permission_checker=None, hook_pipeline=None):
        self._users = {}
        self._permission_checker = permission_checker
        self._hook_pipeline = hook_pipeline

    def _validate_user_data(self, username=None, email=None, role=None, **kwargs):
        if username is not None and not username:
            raise InvalidUserError("Username cannot be empty")
        if email is not None and not email:
            raise InvalidUserError("Email cannot be empty")
        if role is not None and role not in User.VALID_ROLES:
            raise InvalidUserError(f"Invalid role: {role}")

    def add_user(self, username, email, role="member", user_id=None):
        self._validate_user_data(username=username, email=email, role=role)
        new_user_id = str(uuid.uuid4())
        data = {"username": username, "email": email, "role": role}

        if self._hook_pipeline:
            ctx = HookContext(action="create_user", entity_type="user",
                              entity_id=new_user_id, data=data, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "manage_users")

        user = User(
            id=new_user_id,
            username=username,
            email=email,
            role=role,
        )
        self._users[new_user_id] = user

        if self._hook_pipeline:
            ctx.result = user
            self._hook_pipeline.execute_after(ctx)

        return user

    def get_user(self, user_id):
        if user_id not in self._users:
            raise UserNotFoundError(user_id)
        return self._users[user_id]

    def get_user_by_username(self, username):
        username_lower = username.lower()
        for user in self._users.values():
            if user.username.lower() == username_lower:
                return user
        raise UserNotFoundError(username)

    def update_user(self, user_id, admin_user_id=None, **kwargs):
        self._validate_user_data(**kwargs)
        data = kwargs.copy()

        if self._hook_pipeline:
            ctx = HookContext(action="update_user", entity_type="user",
                              entity_id=user_id, data=data, user_id=admin_user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and admin_user_id:
            self._permission_checker.require_permission(admin_user_id, "manage_users")

        user = self.get_user(user_id)
        for key, value in kwargs.items():
            setattr(user, key, value)

        if self._hook_pipeline:
            ctx.result = user
            self._hook_pipeline.execute_after(ctx)

        return user

    def remove_user(self, user_id, admin_user_id=None):
        if user_id not in self._users:
            raise UserNotFoundError(user_id)

        if self._hook_pipeline:
            ctx = HookContext(action="delete_user", entity_type="user",
                              entity_id=user_id, data={}, user_id=admin_user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and admin_user_id:
            self._permission_checker.require_permission(admin_user_id, "manage_users")

        del self._users[user_id]

        if self._hook_pipeline:
            ctx.result = None
            self._hook_pipeline.execute_after(ctx)

    def list_users(self):
        return list(self._users.values())

    @property
    def count(self):
        return len(self._users)
