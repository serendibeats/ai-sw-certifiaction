import copy


class Command:
    def execute(self):
        raise NotImplementedError

    def undo(self):
        raise NotImplementedError

    @property
    def description(self):
        return self.__class__.__name__


class CreateTaskCommand(Command):
    def __init__(self, task_manager, title, description="", priority=None,
                 project_id=None, assignee_id=None, tags=None, story_points=0,
                 user_id=None):
        self._task_manager = task_manager
        self._title = title
        self._description = description
        self._priority = priority
        self._project_id = project_id
        self._assignee_id = assignee_id
        self._tags = tags
        self._story_points = story_points
        self._user_id = user_id
        self._created_task = None

    def execute(self):
        kwargs = {
            "title": self._title,
            "description": self._description,
            "project_id": self._project_id,
            "assignee_id": self._assignee_id,
            "tags": self._tags,
            "story_points": self._story_points,
        }
        if self._priority is not None:
            kwargs["priority"] = self._priority
        self._created_task = self._task_manager._add_task_internal(**kwargs)
        return self._created_task

    def undo(self):
        if self._created_task:
            self._task_manager._remove_task_internal(self._created_task.id)

    @property
    def description(self):
        return f"CreateTask: {self._title}"


class UpdateTaskCommand(Command):
    def __init__(self, task_manager, task_id, **kwargs):
        self._task_manager = task_manager
        self._task_id = task_id
        self._kwargs = kwargs
        self._previous_state = None

    def execute(self):
        task = self._task_manager.get_task(self._task_id)
        self._previous_state = {k: getattr(task, k) for k in self._kwargs}
        return self._task_manager._update_task_internal(self._task_id, **self._kwargs)

    def undo(self):
        if self._previous_state:
            self._task_manager._update_task_internal(self._task_id, **self._previous_state)

    @property
    def description(self):
        return f"UpdateTask: {self._task_id}"


class DeleteTaskCommand(Command):
    def __init__(self, task_manager, task_id):
        self._task_manager = task_manager
        self._task_id = task_id
        self._deleted_task = None

    def execute(self):
        self._deleted_task = self._task_manager._remove_task_internal(self._task_id)
        return self._deleted_task

    def undo(self):
        if self._deleted_task:
            t = self._deleted_task
            self._task_manager._tasks[t.id] = t

    @property
    def description(self):
        return f"DeleteTask: {self._task_id}"


class CreateProjectCommand(Command):
    def __init__(self, project_manager, name, description="", owner_id=None,
                 user_id=None):
        self._project_manager = project_manager
        self._name = name
        self._description = description
        self._owner_id = owner_id
        self._user_id = user_id
        self._created_project = None

    def execute(self):
        self._created_project = self._project_manager._add_project_internal(
            name=self._name, description=self._description, owner_id=self._owner_id)
        return self._created_project

    def undo(self):
        if self._created_project:
            self._project_manager._remove_project_internal(self._created_project.id)

    @property
    def description(self):
        return f"CreateProject: {self._name}"


class UpdateProjectCommand(Command):
    def __init__(self, project_manager, project_id, **kwargs):
        self._project_manager = project_manager
        self._project_id = project_id
        self._kwargs = kwargs
        self._previous_state = None

    def execute(self):
        project = self._project_manager.get_project(self._project_id)
        self._previous_state = {k: getattr(project, k) for k in self._kwargs}
        return self._project_manager._update_project_internal(self._project_id, **self._kwargs)

    def undo(self):
        if self._previous_state:
            self._project_manager._update_project_internal(self._project_id, **self._previous_state)

    @property
    def description(self):
        return f"UpdateProject: {self._project_id}"


class DeleteProjectCommand(Command):
    def __init__(self, project_manager, project_id):
        self._project_manager = project_manager
        self._project_id = project_id
        self._deleted_project = None
        self._deleted_tasks = []
        self._deleted_comments = {}  # (entity_type, entity_id) -> comments
        self._deleted_dependencies = {}  # task_id -> set of dep ids

    def execute(self):
        # Save tasks that will be cascade-deleted
        if self._project_manager._task_manager:
            tasks = self._project_manager._task_manager.get_tasks_by_project(self._project_id)
            self._deleted_tasks = list(tasks)

            # Save dependencies and comments for each task
            if self._project_manager._relation_manager:
                rm = self._project_manager._relation_manager
                for task in tasks:
                    deps = rm.get_dependencies(task.id)
                    if deps:
                        self._deleted_dependencies[task.id] = set(deps)
                    comments = rm.get_comments("task", task.id)
                    if comments:
                        self._deleted_comments[("task", task.id)] = list(comments)

                # Save project comments
                proj_comments = rm.get_comments("project", self._project_id)
                if proj_comments:
                    self._deleted_comments[("project", self._project_id)] = list(proj_comments)

        self._deleted_project = self._project_manager._remove_project_internal(self._project_id)
        return self._deleted_project

    def undo(self):
        if self._deleted_project:
            p = self._deleted_project
            self._project_manager._projects[p.id] = p

            # Restore tasks
            if self._project_manager._task_manager:
                for task in self._deleted_tasks:
                    self._project_manager._task_manager._tasks[task.id] = task

            # Restore dependencies and comments
            if self._project_manager._relation_manager:
                rm = self._project_manager._relation_manager
                for task_id, deps in self._deleted_dependencies.items():
                    if task_id not in rm._dependencies:
                        rm._dependencies[task_id] = set()
                    rm._dependencies[task_id].update(deps)

                for key, comments in self._deleted_comments.items():
                    if key not in rm._comments:
                        rm._comments[key] = []
                    rm._comments[key].extend(comments)

    @property
    def description(self):
        return f"DeleteProject: {self._project_id}"


class HistoryManager:
    def __init__(self, max_size=100):
        self._max_size = max_size
        self._undo_stack = []
        self._redo_stack = []

    def execute(self, command):
        result = command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        return result

    def undo(self):
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        result = command.undo()
        self._redo_stack.append(command)
        return result

    def redo(self):
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        result = command.execute()
        self._undo_stack.append(command)
        return result

    @property
    def can_undo(self):
        return len(self._undo_stack) > 0

    @property
    def can_redo(self):
        return len(self._redo_stack) > 0

    def get_history(self):
        return [cmd.description for cmd in self._undo_stack]
