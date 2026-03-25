"""Step 1: 기초 모델 + 매니저 CRUD 테스트."""
import time
import pytest
from models import (
    Task, TaskStatus, TaskPriority,
    Project, ProjectStatus,
    User,
)
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from exceptions import (
    TaskNotFoundError, ProjectNotFoundError, UserNotFoundError,
    InvalidTransitionError,
)


# ── Task 모델 테스트 ──

class TestTaskModel:
    def test_task_creation_defaults(self):
        t = Task(id="t1", title="테스트 태스크")
        assert t.id == "t1"
        assert t.title == "테스트 태스크"
        assert t.status == TaskStatus.TODO
        assert t.priority == TaskPriority.MEDIUM
        assert t.tags == []
        assert t.metadata == {}
        assert t.description == ""
        assert t.project_id is None
        assert t.assignee_id is None

    def test_task_creation_with_values(self):
        t = Task(id="t1", title="태스크", description="설명",
                 priority=TaskPriority.HIGH, project_id="p1",
                 assignee_id="u1", tags=["bug", "urgent"])
        assert t.priority == TaskPriority.HIGH
        assert t.project_id == "p1"
        assert t.assignee_id == "u1"
        assert t.tags == ["bug", "urgent"]

    def test_task_to_dict(self):
        t = Task(id="t1", title="태스크", tags=["a"])
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["status"] == "TODO"
        assert d["priority"] == "MEDIUM"
        assert d["tags"] == ["a"]

    def test_task_update(self):
        t = Task(id="t1", title="원래 제목")
        old_updated = t.updated_at
        time.sleep(0.01)
        t.update(title="새 제목", description="설명 추가")
        assert t.title == "새 제목"
        assert t.description == "설명 추가"
        assert t.updated_at > old_updated

    def test_task_valid_transition(self):
        t = Task(id="t1", title="태스크")
        assert t.transition_to(TaskStatus.IN_PROGRESS) is True
        assert t.status == TaskStatus.IN_PROGRESS
        assert t.transition_to(TaskStatus.IN_REVIEW) is True
        assert t.status == TaskStatus.IN_REVIEW
        assert t.transition_to(TaskStatus.DONE) is True
        assert t.status == TaskStatus.DONE

    def test_task_invalid_transition(self):
        t = Task(id="t1", title="태스크", status=TaskStatus.DONE)
        with pytest.raises(InvalidTransitionError):
            t.transition_to(TaskStatus.TODO)

    def test_task_cancel_from_any(self):
        for status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE]:
            t = Task(id="t1", title="태스크", status=status)
            t.transition_to(TaskStatus.CANCELLED)
            assert t.status == TaskStatus.CANCELLED

    def test_task_cancel_is_terminal(self):
        t = Task(id="t1", title="태스크", status=TaskStatus.CANCELLED)
        with pytest.raises(InvalidTransitionError):
            t.transition_to(TaskStatus.TODO)

    def test_task_equality(self):
        t1 = Task(id="t1", title="A")
        t2 = Task(id="t1", title="B")
        assert t1 == t2
        assert hash(t1) == hash(t2)


# ── Project 모델 테스트 ──

class TestProjectModel:
    def test_project_creation(self):
        p = Project(id="p1", name="프로젝트")
        assert p.id == "p1"
        assert p.name == "프로젝트"
        assert p.status == ProjectStatus.ACTIVE
        assert p.metadata == {}

    def test_project_to_dict(self):
        p = Project(id="p1", name="프로젝트")
        d = p.to_dict()
        assert d["id"] == "p1"
        assert d["status"] == "ACTIVE"

    def test_project_update(self):
        p = Project(id="p1", name="원래")
        time.sleep(0.01)
        p.update(name="변경됨")
        assert p.name == "변경됨"


# ── User 모델 테스트 ──

class TestUserModel:
    def test_user_creation(self):
        u = User(id="u1", username="alice", email="alice@test.com")
        assert u.id == "u1"
        assert u.username == "alice"
        assert u.role == "member"

    def test_user_to_dict(self):
        u = User(id="u1", username="alice", email="alice@test.com", role="admin")
        d = u.to_dict()
        assert d["role"] == "admin"

    def test_user_equality(self):
        u1 = User(id="u1", username="alice", email="a@a.com")
        u2 = User(id="u1", username="bob", email="b@b.com")
        assert u1 == u2


# ── TaskManager 테스트 ──

class TestTaskManager:
    def test_add_and_get_task(self):
        tm = TaskManager()
        t = tm.add_task("태스크 1", description="설명")
        assert t.title == "태스크 1"
        fetched = tm.get_task(t.id)
        assert fetched.id == t.id

    def test_get_nonexistent_task(self):
        tm = TaskManager()
        with pytest.raises(TaskNotFoundError):
            tm.get_task("nonexistent")

    def test_update_task(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        tm.update_task(t.id, title="변경됨")
        assert tm.get_task(t.id).title == "변경됨"

    def test_remove_task(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        tm.remove_task(t.id)
        with pytest.raises(TaskNotFoundError):
            tm.get_task(t.id)

    def test_list_tasks(self):
        tm = TaskManager()
        tm.add_task("A")
        tm.add_task("B")
        assert len(tm.list_tasks()) == 2

    def test_count(self):
        tm = TaskManager()
        assert tm.count == 0
        tm.add_task("A")
        assert tm.count == 1

    def test_get_tasks_by_project(self):
        tm = TaskManager()
        tm.add_task("A", project_id="p1")
        tm.add_task("B", project_id="p2")
        tm.add_task("C", project_id="p1")
        assert len(tm.get_tasks_by_project("p1")) == 2

    def test_get_tasks_by_assignee(self):
        tm = TaskManager()
        tm.add_task("A", assignee_id="u1")
        tm.add_task("B", assignee_id="u2")
        assert len(tm.get_tasks_by_assignee("u1")) == 1

    def test_get_tasks_by_status(self):
        tm = TaskManager()
        tm.add_task("A")
        tm.add_task("B")
        assert len(tm.get_tasks_by_status(TaskStatus.TODO)) == 2

    def test_get_tasks_by_priority(self):
        tm = TaskManager()
        tm.add_task("A", priority=TaskPriority.HIGH)
        tm.add_task("B", priority=TaskPriority.LOW)
        assert len(tm.get_tasks_by_priority(TaskPriority.HIGH)) == 1

    def test_search_tasks(self):
        tm = TaskManager()
        tm.add_task("로그인 버그 수정", description="긴급")
        tm.add_task("회원가입 기능", description="로그인 연동 필요")
        tm.add_task("대시보드 개선")
        results = tm.search_tasks("로그인")
        assert len(results) == 2


# ── ProjectManager 테스트 ──

class TestProjectManager:
    def test_add_and_get_project(self):
        pm = ProjectManager()
        p = pm.add_project("프로젝트 1")
        assert p.name == "프로젝트 1"
        assert pm.get_project(p.id).id == p.id

    def test_get_nonexistent_project(self):
        pm = ProjectManager()
        with pytest.raises(ProjectNotFoundError):
            pm.get_project("nonexistent")

    def test_update_project(self):
        pm = ProjectManager()
        p = pm.add_project("프로젝트")
        pm.update_project(p.id, name="변경됨")
        assert pm.get_project(p.id).name == "변경됨"

    def test_remove_project(self):
        pm = ProjectManager()
        p = pm.add_project("프로젝트")
        pm.remove_project(p.id)
        with pytest.raises(ProjectNotFoundError):
            pm.get_project(p.id)

    def test_list_and_count(self):
        pm = ProjectManager()
        pm.add_project("A")
        pm.add_project("B")
        assert len(pm.list_projects()) == 2
        assert pm.count == 2

    def test_search_projects(self):
        pm = ProjectManager()
        pm.add_project("웹 서비스 개발", description="프론트엔드")
        pm.add_project("모바일 앱", description="iOS/Android")
        results = pm.search_projects("개발")
        assert len(results) == 1


# ── UserManager 테스트 ──

class TestUserManager:
    def test_add_and_get_user(self):
        um = UserManager()
        u = um.add_user("alice", "alice@test.com")
        assert u.username == "alice"
        assert um.get_user(u.id).id == u.id

    def test_get_nonexistent_user(self):
        um = UserManager()
        with pytest.raises(UserNotFoundError):
            um.get_user("nonexistent")

    def test_get_user_by_username(self):
        um = UserManager()
        u = um.add_user("Alice", "alice@test.com")
        found = um.get_user_by_username("alice")
        assert found.id == u.id

    def test_update_user(self):
        um = UserManager()
        u = um.add_user("alice", "alice@test.com")
        um.update_user(u.id, email="newalice@test.com")
        assert um.get_user(u.id).email == "newalice@test.com"

    def test_remove_user(self):
        um = UserManager()
        u = um.add_user("alice", "alice@test.com")
        um.remove_user(u.id)
        with pytest.raises(UserNotFoundError):
            um.get_user(u.id)

    def test_list_and_count(self):
        um = UserManager()
        um.add_user("alice", "a@a.com")
        um.add_user("bob", "b@b.com")
        assert len(um.list_users()) == 2
        assert um.count == 2
