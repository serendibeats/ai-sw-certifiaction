import copy
import time
import uuid
from enum import Enum

from exceptions import InvalidTransitionError


class TaskStatus(Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Valid transitions: from_status -> set of valid to_statuses
VALID_TRANSITIONS = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_REVIEW, TaskStatus.TODO, TaskStatus.CANCELLED},
    TaskStatus.IN_REVIEW: {TaskStatus.DONE, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: set(),
}

COMPLEXITY_POINTS = {
    "trivial": 1,
    "simple": 2,
    "medium": 3,
    "complex": 5,
    "epic": 8,
}


class Task:
    def __init__(self, id=None, title="", description="", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, project_id=None, assignee_id=None,
                 tags=None, created_at=None, updated_at=None, metadata=None,
                 story_points=0):
        self.id = id if id is not None else str(uuid.uuid4())
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.project_id = project_id
        self.assignee_id = assignee_id
        self._tags = list(tags) if tags is not None else []
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self._metadata = dict(metadata) if metadata is not None else {}
        # Handle backward compatibility: if story_points is explicitly set
        if story_points != 0:
            self._metadata["story_points"] = story_points

    @property
    def tags(self):
        return list(self._tags)

    @tags.setter
    def tags(self, value):
        self._tags = list(value) if value is not None else []

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)

    @metadata.setter
    def metadata(self, value):
        self._metadata = dict(value) if value is not None else {}

    @property
    def story_points(self):
        # Explicit story_points in metadata takes priority
        if "story_points" in self._metadata:
            return self._metadata["story_points"]
        # Calculate from complexity
        complexity = self._metadata.get("complexity", "medium")
        return COMPLEXITY_POINTS.get(complexity, 3)

    @story_points.setter
    def story_points(self, value):
        self._metadata["story_points"] = value

    def transition_to(self, new_status):
        if new_status not in VALID_TRANSITIONS.get(self.status, set()):
            raise InvalidTransitionError(self.status, new_status)
        self.status = new_status
        self.updated_at = time.time()
        return True

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "priority": self.priority.value if isinstance(self.priority, Enum) else self.priority,
            "project_id": self.project_id,
            "assignee_id": self.assignee_id,
            "tags": list(self._tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy.deepcopy(self._metadata),
            "story_points": self.story_points,
        }

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)


class ProjectStatus(Enum):
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Project:
    def __init__(self, id=None, name="", description="", owner_id=None,
                 status=ProjectStatus.ACTIVE, created_at=None, updated_at=None,
                 metadata=None, task_manager=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.status = status
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self._metadata = dict(metadata) if metadata is not None else {}
        self._task_manager = task_manager

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)

    @metadata.setter
    def metadata(self, value):
        self._metadata = dict(value) if value is not None else {}

    @property
    def progress(self):
        if self._task_manager is None:
            return 0.0
        tasks = self._task_manager.get_tasks_by_project(self.id)
        if not tasks:
            return 0.0
        done_count = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        return done_count / len(tasks)

    @property
    def health(self):
        if self._task_manager is None:
            return "unknown"
        p = self.progress
        if p >= 0.7:
            return "healthy"
        elif p >= 0.3:
            return "at_risk"
        else:
            return "critical"

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy.deepcopy(self._metadata),
            "progress": self.progress,
            "health": self.health,
        }

    def __eq__(self, other):
        if isinstance(other, Project):
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)


class User:
    VALID_ROLES = {"admin", "manager", "member", "viewer"}

    def __init__(self, id=None, username="", email="", role="member", created_at=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.username = username
        self.email = email
        self.role = role
        self.created_at = created_at if created_at is not None else time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at,
        }

    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)
