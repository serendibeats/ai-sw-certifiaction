import uuid

from models import Project, ProjectStatus
from exceptions import ProjectNotFoundError, InvalidProjectError
from hooks import HookContext


class ProjectManager:
    def __init__(self, permission_checker=None, hook_pipeline=None,
                 relation_manager=None, task_manager=None):
        self._projects = {}
        self._permission_checker = permission_checker
        self._hook_pipeline = hook_pipeline
        self._relation_manager = relation_manager
        self._task_manager = task_manager

    def _validate_project_data(self, name=None, status=None, **kwargs):
        if name is not None and not name:
            raise InvalidProjectError("Name cannot be empty")
        if status is not None and not isinstance(status, ProjectStatus):
            raise InvalidProjectError(f"Invalid status: {status}")

    def _add_project_internal(self, name, description="", owner_id=None):
        self._validate_project_data(name=name)
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name=name,
            description=description,
            owner_id=owner_id,
            task_manager=self._task_manager,
        )
        self._projects[project_id] = project
        return project

    def _update_project_internal(self, project_id, **kwargs):
        self._validate_project_data(**kwargs)
        project = self.get_project(project_id)
        project.update(**kwargs)
        return project

    def _remove_project_internal(self, project_id):
        if project_id not in self._projects:
            raise ProjectNotFoundError(project_id)

        # Cascade: remove all tasks belonging to this project
        if self._task_manager:
            tasks = self._task_manager.get_tasks_by_project(project_id)
            for task in tasks:
                self._task_manager._remove_task_internal(task.id)

        # Remove project comments
        if self._relation_manager:
            self._relation_manager.remove_comments_for_entity("project", project_id)

        project = self._projects.pop(project_id)
        return project

    def add_project(self, name, description="", owner_id=None, user_id=None):
        self._validate_project_data(name=name)
        project_id = str(uuid.uuid4())
        data = {"name": name, "description": description, "owner_id": owner_id}

        if self._hook_pipeline:
            ctx = HookContext(action="create_project", entity_type="project",
                              entity_id=project_id, data=data, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "create_project")

        project = Project(
            id=project_id,
            name=name,
            description=description,
            owner_id=owner_id,
            task_manager=self._task_manager,
        )
        self._projects[project_id] = project

        if self._hook_pipeline:
            ctx.result = project
            self._hook_pipeline.execute_after(ctx)

        return project

    def get_project(self, project_id):
        if project_id not in self._projects:
            raise ProjectNotFoundError(project_id)
        return self._projects[project_id]

    def update_project(self, project_id, user_id=None, **kwargs):
        self._validate_project_data(**kwargs)
        project = self.get_project(project_id)

        if self._hook_pipeline:
            ctx = HookContext(action="update_project", entity_type="project",
                              entity_id=project_id, data=kwargs, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "update_project")

        project.update(**kwargs)

        if self._hook_pipeline:
            ctx.result = project
            self._hook_pipeline.execute_after(ctx)

        return project

    def remove_project(self, project_id, user_id=None):
        if project_id not in self._projects:
            raise ProjectNotFoundError(project_id)

        if self._hook_pipeline:
            ctx = HookContext(action="delete_project", entity_type="project",
                              entity_id=project_id, data={}, user_id=user_id)
            self._hook_pipeline.execute_before(ctx)

        if self._permission_checker and user_id:
            self._permission_checker.require_permission(user_id, "delete_project")

        # Cascade: remove all tasks belonging to this project
        if self._task_manager:
            tasks = self._task_manager.get_tasks_by_project(project_id)
            for task in tasks:
                self._task_manager._remove_task_internal(task.id)

        # Remove project comments
        if self._relation_manager:
            self._relation_manager.remove_comments_for_entity("project", project_id)

        del self._projects[project_id]

        if self._hook_pipeline:
            ctx.result = None
            self._hook_pipeline.execute_after(ctx)

    def list_projects(self):
        return list(self._projects.values())

    def search_projects(self, query):
        query_lower = query.lower()
        return [p for p in self._projects.values()
                if query_lower in p.name.lower() or query_lower in p.description.lower()]

    @property
    def count(self):
        return len(self._projects)
