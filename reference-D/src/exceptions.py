class TaskNotFoundError(Exception):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class ProjectNotFoundError(Exception):
    def __init__(self, project_id):
        self.project_id = project_id
        super().__init__(f"Project not found: {project_id}")


class UserNotFoundError(Exception):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class DuplicateTaskError(Exception):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__(f"Duplicate task: {task_id}")


class DuplicateProjectError(Exception):
    def __init__(self, project_id):
        self.project_id = project_id
        super().__init__(f"Duplicate project: {project_id}")


class DuplicateUserError(Exception):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"Duplicate user: {user_id}")


class InvalidTaskError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class InvalidProjectError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class InvalidUserError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class PermissionDeniedError(Exception):
    def __init__(self, user_id, action):
        self.user_id = user_id
        self.action = action
        super().__init__(f"Permission denied for user {user_id}: {action}")


class InvalidTransitionError(Exception):
    def __init__(self, current_status, new_status):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Invalid transition from {current_status} to {new_status}")


class CircularDependencyError(Exception):
    def __init__(self, task_id, depends_on_id):
        self.task_id = task_id
        self.depends_on_id = depends_on_id
        super().__init__(f"Circular dependency: {task_id} -> {depends_on_id}")
