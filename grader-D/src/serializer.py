from models import Task, TaskStatus, TaskPriority, Project, ProjectStatus, User


class TaskSerializer:
    @staticmethod
    def serialize(task):
        return task.to_dict()

    @staticmethod
    def deserialize(data):
        status = data.get("status", "TODO")
        if isinstance(status, str):
            status = TaskStatus(status)

        priority = data.get("priority", "MEDIUM")
        if isinstance(priority, str):
            priority = TaskPriority(priority)

        metadata = data.get("metadata", {})

        # Handle backward compatibility: old format with direct story_points
        story_points = data.get("story_points", 0)
        if story_points and "story_points" not in metadata and "complexity" not in metadata:
            metadata["story_points"] = story_points

        task = Task(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=status,
            priority=priority,
            project_id=data.get("project_id"),
            assignee_id=data.get("assignee_id"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=metadata,
        )
        return task


class ProjectSerializer:
    @staticmethod
    def serialize(project):
        return project.to_dict()

    @staticmethod
    def deserialize(data, task_manager=None):
        status = data.get("status", "ACTIVE")
        if isinstance(status, str):
            status = ProjectStatus(status)

        project = Project(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            owner_id=data.get("owner_id"),
            status=status,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
            task_manager=task_manager,
        )
        return project


class UserSerializer:
    @staticmethod
    def serialize(user):
        return user.to_dict()

    @staticmethod
    def deserialize(data):
        user = User(
            id=data.get("id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            role=data.get("role", "member"),
            created_at=data.get("created_at"),
        )
        return user
