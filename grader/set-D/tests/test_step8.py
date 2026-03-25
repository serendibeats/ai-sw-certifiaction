"""Step 8: 유효성 검증 + 직렬화 + 보고서 + 완료 태스크 추적 테스트."""
import pytest
from models import (
    Task, TaskStatus, TaskPriority,
    Project, ProjectStatus,
    User, COMPLEXITY_POINTS,
)
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from serializer import TaskSerializer, ProjectSerializer, UserSerializer
from hooks import HookPipeline, ValidationHook
from analytics import AnalyticsEngine
from board import Board
from exceptions import InvalidTaskError, InvalidProjectError, InvalidUserError


# ── 유효성 검증 테스트 ──

class TestValidation:
    def test_task_empty_title_internal(self):
        tm = TaskManager()
        with pytest.raises(InvalidTaskError):
            tm._add_task_internal("")

    def test_task_empty_title_public(self):
        tm = TaskManager()
        with pytest.raises(InvalidTaskError):
            tm.add_task("")

    def test_task_empty_title_update(self):
        tm = TaskManager()
        t = tm.add_task("유효한 제목")
        with pytest.raises(InvalidTaskError):
            tm.update_task(t.id, title="")

    def test_project_empty_name_internal(self):
        pm = ProjectManager()
        with pytest.raises(InvalidProjectError):
            pm._add_project_internal("")

    def test_project_empty_name_public(self):
        pm = ProjectManager()
        with pytest.raises(InvalidProjectError):
            pm.add_project("")

    def test_user_empty_username(self):
        um = UserManager()
        with pytest.raises(InvalidUserError):
            um.add_user("", "a@a.com")

    def test_user_empty_email(self):
        um = UserManager()
        with pytest.raises(InvalidUserError):
            um.add_user("alice", "")

    def test_user_invalid_role(self):
        um = UserManager()
        with pytest.raises(InvalidUserError):
            um.add_user("alice", "a@a.com", role="superadmin")

    def test_task_invalid_priority_update(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        with pytest.raises(InvalidTaskError):
            tm.update_task(t.id, priority="INVALID")

    def test_project_invalid_status_update(self):
        pm = ProjectManager()
        p = pm.add_project("프로젝트")
        with pytest.raises(InvalidProjectError):
            pm.update_project(p.id, status="INVALID")


# ── TaskSerializer 테스트 ──

class TestTaskSerializer:
    def test_serialize(self):
        t = Task(id="t1", title="태스크", priority=TaskPriority.HIGH,
                 tags=["bug"], story_points=5)
        d = TaskSerializer.serialize(t)
        assert d["id"] == "t1"
        assert d["priority"] == "HIGH"
        assert d["story_points"] == 5

    def test_deserialize(self):
        data = {
            "id": "t1", "title": "태스크", "description": "",
            "status": "IN_PROGRESS", "priority": "HIGH",
            "project_id": "p1", "assignee_id": "u1",
            "tags": ["bug"], "created_at": 1000, "updated_at": 1001,
            "metadata": {"key": "val"}, "story_points": 5,
        }
        t = TaskSerializer.deserialize(data)
        assert t.id == "t1"
        assert t.status == TaskStatus.IN_PROGRESS
        assert t.priority == TaskPriority.HIGH
        assert t.story_points == 5

    def test_round_trip(self):
        t = Task(id="t1", title="왕복 테스트", priority=TaskPriority.CRITICAL,
                 tags=["a", "b"], story_points=8)
        d = TaskSerializer.serialize(t)
        t2 = TaskSerializer.deserialize(d)
        assert t2.id == t.id
        assert t2.title == t.title
        assert t2.priority == t.priority
        assert t2.story_points == 8

    def test_backward_compat_old_format(self):
        """이전 포맷 (직접 story_points, complexity 없음) 역직렬화."""
        data = {
            "id": "t1", "title": "Old", "story_points": 13,
            "metadata": {},
        }
        t = TaskSerializer.deserialize(data)
        assert t.story_points == 13

    def test_backward_compat_complexity_format(self):
        """새 포맷 (complexity 기반) 역직렬화."""
        data = {
            "id": "t1", "title": "New",
            "metadata": {"complexity": "epic"},
        }
        t = TaskSerializer.deserialize(data)
        assert t.story_points == 8  # epic → 8


# ── ProjectSerializer 테스트 ──

class TestProjectSerializer:
    def test_serialize(self):
        p = Project(id="p1", name="프로젝트", status=ProjectStatus.ACTIVE)
        d = ProjectSerializer.serialize(p)
        assert d["id"] == "p1"
        assert d["status"] == "ACTIVE"

    def test_deserialize(self):
        data = {
            "id": "p1", "name": "프로젝트", "description": "",
            "status": "ON_HOLD", "owner_id": "u1",
            "metadata": {}, "created_at": 1000, "updated_at": 1001,
        }
        p = ProjectSerializer.deserialize(data)
        assert p.status == ProjectStatus.ON_HOLD

    def test_round_trip(self):
        p = Project(id="p1", name="왕복", metadata={"key": "val"})
        d = ProjectSerializer.serialize(p)
        p2 = ProjectSerializer.deserialize(d)
        assert p2.name == p.name
        assert p2._metadata == {"key": "val"}


# ── UserSerializer 테스트 ──

class TestUserSerializer:
    def test_serialize(self):
        u = User(id="u1", username="alice", email="a@a.com", role="admin")
        d = UserSerializer.serialize(u)
        assert d["role"] == "admin"

    def test_deserialize(self):
        data = {"id": "u1", "username": "alice", "email": "a@a.com",
                "role": "manager", "created_at": 1000}
        u = UserSerializer.deserialize(data)
        assert u.role == "manager"

    def test_round_trip(self):
        u = User(id="u1", username="bob", email="b@b.com")
        d = UserSerializer.serialize(u)
        u2 = UserSerializer.deserialize(d)
        assert u2.username == u.username


# ── 완료 태스크 추적 테스트 ──

class TestCompletedTaskTracking:
    def test_completed_tasks_via_update(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        tm.update_task(t.id, status=TaskStatus.IN_PROGRESS)
        tm.update_task(t.id, status=TaskStatus.IN_REVIEW)
        tm.update_task(t.id, status=TaskStatus.DONE)
        completed = tm.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0]["title"] == "태스크"

    def test_completed_tasks_via_board(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        board = Board(tm)
        board.move_task(t.id, TaskStatus.IN_PROGRESS)
        board.move_task(t.id, TaskStatus.IN_REVIEW)
        board.move_task(t.id, TaskStatus.DONE)
        completed = tm.get_completed_tasks()
        assert len(completed) == 1

    def test_completed_tasks_defensive_copy(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        tm.update_task(t.id, status=TaskStatus.IN_PROGRESS)
        tm.update_task(t.id, status=TaskStatus.IN_REVIEW)
        tm.update_task(t.id, status=TaskStatus.DONE)
        tm.get_completed_tasks().clear()
        assert len(tm.get_completed_tasks()) == 1
