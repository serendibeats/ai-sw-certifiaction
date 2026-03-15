import uuid

from models import Task, TaskPriority, TaskStatus
from exceptions import TaskNotFoundError, InvalidTaskError
from hooks import HookContext


class TaskManager:
    def __init__(self, permission_checker=None, hook_pipeline=None, relation_manager=None):
        self._tasks = {}
        self._permission_checker = permission_checker
        self._hook_pipeline = hook_pipeline
        self._relation_manager = relation_manager
        self._completed_snapshots = []

    def _track_completion(self, task):
        """Track task completion by saving a snapshot."""
        if task.status == TaskStatus.DONE:
            self._completed_snapshots.append(task.to_dict())

    def _record_completion(self, task):
        """Record task completion (alias for _track_completion)."""
        self._track_completion(task)

    def get_completed_tasks(self):
        return list(self._completed_snapshots)

    def _validate_task_data(self, title=None, priority=None, story_points=None, **kwargs):
        if title is not None and not title:
            raise InvalidTaskError("Title cannot be empty")
        if priority is not None and not isinstance(priority, TaskPriority):
            raise InvalidTaskError(f"Invalid priority: {priority}")
        if story_points is not None and story_points < 0:
            raise InvalidTaskError("Story points must be >= 0")

    def _add_task_internal(self, title, description="", priority=TaskPriority.MEDIUM,
                           project_id=None, assignee_id=None, tags=None, story_points=0,
                           metadata=None):
        self._validate_task_data(title=title, priority=priority, story_points=story_points)
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            project_id=project_id,
            assignee_id=assignee_id,
            tags=tags if tags is not None else [],
            story_points=story_points,
            metadata=metadata,
        )
        self._tasks[task_id] = task
        return task

    def _update_task_internal(self, task_id, **kwargs):
        self._validate_task_data(**kwargs)
        task = self.get_task(task_id)
        old_status = task.status
        task.update(**kwargs)
        if task.status == TaskStatus.DONE and old_status != TaskStatus.DONE:
            self._track_completion(task)
        return task

    def _remove_task_internal(self, task_id):
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        task = self._tasks.pop(task_id)
        # Cascade: clean up comments and dependencies
        if self._relation_manager:
            self._relation_manager.remove_comments_for_entity("task", task_id)
            self._relation_manager.remove_dependencies_for_task(task_id)
        return task

    def add_task(self, title, description="", priority=TaskPriority.MEDIUM,
                 project_id=None, assignee_id=None, tags=None, story_points=0,
                 user_id=None, metadata=None):
        self._validate_task_data(title=title, priority=priority, story_points=story_points)
        task_id = str(uuid.uuid4())
        data = {"title": title, "description": description, "priority": priority,
                "project_id": project_id, "assignee_id": assignee_id,
                "tags": tags, "story_points": story_points}

        if self._hook_pipeline:
            ctx = HookContext(action="create_task", entity_type="task",
                              entity_id=task_id, data=data, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "create_task")

        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            project_id=project_id,
            assignee_id=assignee_id,
            tags=tags if tags is not None else [],
            story_points=story_points,
            metadata=metadata,
        )
        self._tasks[task_id] = task

        if self._hook_pipeline:
            ctx.result = task
            self._hook_pipeline.execute_after(ctx)

        return task

    def get_task(self, task_id):
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        return self._tasks[task_id]

    def update_task(self, task_id, user_id=None, **kwargs):
        self._validate_task_data(**kwargs)
        task = self.get_task(task_id)
        old_status = task.status

        if self._hook_pipeline:
            ctx = HookContext(action="update_task", entity_type="task",
                              entity_id=task_id, data=kwargs, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "update_task", task)

        task.update(**kwargs)

        # Track completion if status changed to DONE
        if task.status == TaskStatus.DONE and old_status != TaskStatus.DONE:
            self._track_completion(task)

        if self._hook_pipeline:
            ctx.result = task
            self._hook_pipeline.execute_after(ctx)

        return task

    def remove_task(self, task_id, user_id=None):
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        task = self._tasks[task_id]

        if self._hook_pipeline:
            ctx = HookContext(action="delete_task", entity_type="task",
                              entity_id=task_id, data={}, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "delete_task", task)

        del self._tasks[task_id]

        # Cascade cleanup
        if self._relation_manager:
            self._relation_manager.remove_comments_for_entity("task", task_id)
            self._relation_manager.remove_dependencies_for_task(task_id)

        if self._hook_pipeline:
            ctx.result = None
            self._hook_pipeline.execute_after(ctx)

    def list_tasks(self):
        return list(self._tasks.values())

    def get_tasks_by_project(self, project_id):
        return [t for t in self._tasks.values() if t.project_id == project_id]

    def get_tasks_by_assignee(self, assignee_id):
        return [t for t in self._tasks.values() if t.assignee_id == assignee_id]

    def get_tasks_by_status(self, status):
        return [t for t in self._tasks.values() if t.status == status]

    def get_tasks_by_priority(self, priority):
        return [t for t in self._tasks.values() if t.priority == priority]

    def search_tasks(self, query):
        query_lower = query.lower()
        return [t for t in self._tasks.values()
                if query_lower in t.title.lower() or query_lower in t.description.lower()]

    @property
    def count(self):
        return len(self._tasks)

    def filter_tasks(self, status=None, priority=None, assignee_id=None,
                     project_id=None, tags=None):
        results = list(self._tasks.values())
        if status is not None:
            results = [t for t in results if t.status == status]
        if priority is not None:
            results = [t for t in results if t.priority == priority]
        if assignee_id is not None:
            results = [t for t in results if t.assignee_id == assignee_id]
        if project_id is not None:
            results = [t for t in results if t.project_id == project_id]
        if tags is not None:
            results = [t for t in results
                       if all(any(tag.lower() == tt.lower() for tt in t._tags) for tag in tags)]
        return results

    def sort_tasks(self, tasks, key="created_at", reverse=False):
        PRIORITY_ORDER = {
            TaskPriority.CRITICAL: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1,
        }
        if key == "priority":
            return sorted(tasks, key=lambda t: PRIORITY_ORDER.get(t.priority, 0), reverse=not reverse)
        return sorted(tasks, key=lambda t: getattr(t, key), reverse=reverse)

    def get_task_statistics(self):
        tasks = list(self._tasks.values())
        total = len(tasks)
        by_status = {}
        for status in TaskStatus:
            count = len([t for t in tasks if t.status == status])
            by_status[status.value] = count
        by_priority = {}
        for priority in TaskPriority:
            count = len([t for t in tasks if t.priority == priority])
            by_priority[priority.value] = count
        avg_sp = sum(t.story_points for t in tasks) / total if total > 0 else 0
        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "avg_story_points": avg_sp,
        }
