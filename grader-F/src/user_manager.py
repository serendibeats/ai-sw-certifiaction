from models import User, UserStatus
from exceptions import UserNotFoundError, DuplicateUserError


class UserManager:
    def __init__(self):
        self._users = {}

    def add_user(self, username, display_name="", email=""):
        for user in self._users.values():
            if user.username.lower() == username.lower():
                raise DuplicateUserError(username)
        user = User(username=username, display_name=display_name, email=email)
        self._users[user.id] = user
        return user

    def get_user(self, user_id):
        if user_id not in self._users:
            raise UserNotFoundError(user_id)
        return self._users[user_id]

    def get_user_by_username(self, username):
        for user in self._users.values():
            if user.username.lower() == username.lower():
                return user
        raise UserNotFoundError(username)

    def update_user(self, user_id, **kwargs):
        user = self.get_user(user_id)
        user.update(**kwargs)
        return user

    def remove_user(self, user_id):
        if user_id not in self._users:
            raise UserNotFoundError(user_id)
        del self._users[user_id]

    def list_users(self):
        return list(self._users.values())

    def set_status(self, user_id, status):
        user = self.get_user(user_id)
        user.status = status
        return user

    def search_users(self, query):
        query_lower = query.lower()
        return [
            user for user in self._users.values()
            if query_lower in user.username.lower() or query_lower in user.display_name.lower()
        ]

    @property
    def count(self):
        return len(self._users)
