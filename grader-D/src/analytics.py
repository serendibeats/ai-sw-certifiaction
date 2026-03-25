import time

from models import TaskStatus


class AnalyticsEngine:
    def __init__(self, task_manager, project_manager, user_manager=None):
        self._task_manager = task_manager
        self._project_manager = project_manager
        self._user_manager = user_manager

    def get_velocity(self, project_id, days=7):
        cutoff = time.time() - (days * 86400)
        tasks = self._task_manager.get_tasks_by_project(project_id)
        completed = [t for t in tasks
                     if t.status == TaskStatus.DONE and t.updated_at >= cutoff]
        completed_points = sum(t.story_points for t in completed)
        return {
            "completed_points": completed_points,
            "completed_count": len(completed),
        }

    def get_workload_distribution(self):
        tasks = self._task_manager.list_tasks()
        distribution = {}
        for task in tasks:
            if task.assignee_id is not None:
                distribution[task.assignee_id] = distribution.get(task.assignee_id, 0) + 1
        return distribution

    def get_project_summary(self, project_id):
        project = self._project_manager.get_project(project_id)
        tasks = self._task_manager.get_tasks_by_project(project_id)

        by_status = {}
        for status in TaskStatus:
            by_status[status.value] = len([t for t in tasks if t.status == status])

        return {
            "name": project.name,
            "progress": project.progress,
            "health": project.health,
            "total_tasks": len(tasks),
            "by_status": by_status,
        }

    def get_team_report(self, project_id):
        tasks = self._task_manager.get_tasks_by_project(project_id)
        members = {}
        for task in tasks:
            uid = task.assignee_id
            if uid is not None:
                if uid not in members:
                    members[uid] = {"assigned": 0, "completed": 0, "in_progress": 0}
                members[uid]["assigned"] += 1
                if task.status == TaskStatus.DONE:
                    members[uid]["completed"] += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    members[uid]["in_progress"] += 1
        return {"members": members}

    def get_burndown_data(self, project_id):
        tasks = self._task_manager.get_tasks_by_project(project_id)
        # Return snapshot data based on completed tasks
        completed_snapshots = self._task_manager.get_completed_tasks()
        project_snapshots = [s for s in completed_snapshots
                             if s.get("project_id") == project_id]

        total = len(tasks)
        burndown = []

        # Sort by updated_at (completion time)
        sorted_snapshots = sorted(project_snapshots, key=lambda s: s["updated_at"])

        remaining = total
        for snapshot in sorted_snapshots:
            remaining -= 1
            burndown.append({
                "timestamp": snapshot["updated_at"],
                "remaining": remaining,
                "completed": total - remaining,
            })

        return burndown
