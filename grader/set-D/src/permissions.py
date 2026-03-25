from exceptions import PermissionDeniedError, UserNotFoundError


ROLE_PERMISSIONS = {
    "admin": {"create_task", "update_task", "delete_task", "create_project",
              "update_project", "delete_project", "manage_users", "view"},
    "manager": {"create_task", "update_task", "delete_task", "create_project",
                "update_project", "delete_project", "view"},
    "member": {"create_task", "update_task", "delete_task", "view"},
    "viewer": {"view"},
}


class PermissionChecker:
    def __init__(self, user_manager):
        self._user_manager = user_manager

    def check_permission(self, user_id, action, resource=None):
        try:
            user = self._user_manager.get_user(user_id)
        except UserNotFoundError:
            return False
        allowed = ROLE_PERMISSIONS.get(user.role, set())
        if action not in allowed:
            return False
        # member can only update/delete their own tasks
        if user.role == "member" and action in ("update_task", "delete_task") and resource is not None:
            if resource.assignee_id != user_id:
                return False
        return True

    def require_permission(self, user_id, action, resource=None):
        if not self.check_permission(user_id, action, resource):
            raise PermissionDeniedError(user_id, action)
