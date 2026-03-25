import time
import uuid
from exceptions import CircularDependencyError


class RelationManager:
    def __init__(self, task_manager, project_manager):
        self._task_manager = task_manager
        self._project_manager = project_manager
        # task_id -> set of task_ids it depends on
        self._dependencies = {}
        # (entity_type, entity_id) -> list of comments
        self._comments = {}

    def add_dependency(self, task_id, depends_on_task_id):
        # Validate both tasks exist
        self._task_manager.get_task(task_id)
        self._task_manager.get_task(depends_on_task_id)

        if self.has_circular_dependency(task_id, depends_on_task_id):
            raise CircularDependencyError(task_id, depends_on_task_id)

        if task_id not in self._dependencies:
            self._dependencies[task_id] = set()
        self._dependencies[task_id].add(depends_on_task_id)

    def remove_dependency(self, task_id, depends_on_task_id):
        if task_id in self._dependencies:
            self._dependencies[task_id].discard(depends_on_task_id)

    def get_dependencies(self, task_id):
        return list(self._dependencies.get(task_id, set()))

    def get_dependents(self, task_id):
        dependents = []
        for tid, deps in self._dependencies.items():
            if task_id in deps:
                dependents.append(tid)
        return dependents

    def has_circular_dependency(self, task_id, depends_on_task_id):
        # Check if adding task_id -> depends_on_task_id would create a cycle
        # i.e., check if depends_on_task_id can reach task_id through existing deps
        if task_id == depends_on_task_id:
            return True
        visited = set()
        stack = [depends_on_task_id]
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for dep in self._dependencies.get(current, set()):
                stack.append(dep)
        return False

    def add_comment(self, entity_type, entity_id, user_id, content):
        key = (entity_type, entity_id)
        if key not in self._comments:
            self._comments[key] = []
        comment = {
            "id": str(uuid.uuid4()),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "content": content,
            "created_at": time.time(),
        }
        self._comments[key].append(comment)
        return comment

    def get_comments(self, entity_type, entity_id):
        key = (entity_type, entity_id)
        return list(self._comments.get(key, []))

    def remove_comments_for_entity(self, entity_type, entity_id):
        key = (entity_type, entity_id)
        if key in self._comments:
            del self._comments[key]

    def remove_dependencies_for_task(self, task_id):
        """Remove all dependencies involving this task."""
        # Remove as dependent
        if task_id in self._dependencies:
            del self._dependencies[task_id]
        # Remove from others' dependencies
        for tid in list(self._dependencies.keys()):
            self._dependencies[tid].discard(task_id)
