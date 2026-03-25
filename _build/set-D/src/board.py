from models import TaskStatus


class Board:
    def __init__(self, task_manager, project_id=None):
        self._task_manager = task_manager
        self._project_id = project_id
        self._wip_limits = {}

    def _get_tasks(self):
        if self._project_id:
            return self._task_manager.get_tasks_by_project(self._project_id)
        return self._task_manager.list_tasks()

    def get_columns(self):
        columns = {status: [] for status in TaskStatus}
        for task in self._get_tasks():
            columns[task.status].append(task)
        return columns

    def get_column(self, status):
        return [t for t in self._get_tasks() if t.status == status]

    def move_task(self, task_id, new_status):
        task = self._task_manager.get_task(task_id)
        task.transition_to(new_status)
        # Track completion
        if hasattr(self._task_manager, '_track_completion'):
            self._task_manager._track_completion(task)
        return task

    def get_wip_count(self, status):
        return len(self.get_column(status))

    def set_wip_limit(self, status, limit):
        self._wip_limits[status] = limit

    def check_wip_limit(self, status):
        if status not in self._wip_limits:
            return True
        return self.get_wip_count(status) < self._wip_limits[status]
