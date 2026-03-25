"""Step 3: 권한 시스템 + 시스템 정책 (대소문자 무시, 방어적 복사) 테스트."""
import pytest
from models import Task, TaskStatus, TaskPriority, Project, ProjectStatus, User
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from permissions import PermissionChecker
from exceptions import PermissionDeniedError, UserNotFoundError


def _make_system():
    """테스트용 시스템 구성 (권한 포함)."""
    um = UserManager()
    admin = um.add_user("admin", "admin@test.com", role="admin")
    manager = um.add_user("manager", "mgr@test.com", role="manager")
    member = um.add_user("member", "mem@test.com", role="member")
    viewer = um.add_user("viewer", "view@test.com", role="viewer")
    pc = PermissionChecker(um)
    tm = TaskManager(permission_checker=pc)
    pm = ProjectManager(permission_checker=pc)
    return um, pc, tm, pm, admin, manager, member, viewer


# ── 권한 검사 테스트 ──

class TestPermissionChecker:
    def test_admin_all_permissions(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        for action in ["create_task", "update_task", "delete_task",
                        "create_project", "update_project", "delete_project",
                        "manage_users", "view"]:
            assert pc.check_permission(admin.id, action) is True

    def test_manager_no_manage_users(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        assert pc.check_permission(manager.id, "create_task") is True
        assert pc.check_permission(manager.id, "manage_users") is False

    def test_member_limited_actions(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        assert pc.check_permission(member.id, "create_task") is True
        assert pc.check_permission(member.id, "view") is True
        assert pc.check_permission(member.id, "create_project") is False
        assert pc.check_permission(member.id, "manage_users") is False

    def test_viewer_view_only(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        assert pc.check_permission(viewer.id, "view") is True
        assert pc.check_permission(viewer.id, "create_task") is False

    def test_member_own_task_only(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        task = tm.add_task("테스트", assignee_id=member.id, user_id=admin.id)
        # member가 자기 태스크 수정 가능
        assert pc.check_permission(member.id, "update_task", resource=task) is True
        # 다른 사람의 태스크는 수정 불가
        other_task = tm.add_task("다른 태스크", assignee_id=admin.id, user_id=admin.id)
        assert pc.check_permission(member.id, "update_task", resource=other_task) is False

    def test_require_permission_raises(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        with pytest.raises(PermissionDeniedError):
            pc.require_permission(viewer.id, "create_task")

    def test_nonexistent_user(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        assert pc.check_permission("ghost", "view") is False


# ── TaskManager 권한 통합 테스트 ──

class TestTaskManagerPermissions:
    def test_admin_can_add_task(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        t = tm.add_task("관리자 태스크", user_id=admin.id)
        assert t.title == "관리자 태스크"

    def test_viewer_cannot_add_task(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        with pytest.raises(PermissionDeniedError):
            tm.add_task("뷰어 태스크", user_id=viewer.id)

    def test_member_can_update_own_task(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        t = tm.add_task("멤버 태스크", assignee_id=member.id, user_id=admin.id)
        tm.update_task(t.id, user_id=member.id, title="수정됨")
        assert tm.get_task(t.id).title == "수정됨"

    def test_member_cannot_update_others_task(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        t = tm.add_task("관리자 태스크", assignee_id=admin.id, user_id=admin.id)
        with pytest.raises(PermissionDeniedError):
            tm.update_task(t.id, user_id=member.id, title="수정 시도")

    def test_member_cannot_delete_others_task(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        t = tm.add_task("관리자 태스크", assignee_id=admin.id, user_id=admin.id)
        with pytest.raises(PermissionDeniedError):
            tm.remove_task(t.id, user_id=member.id)

    def test_no_permission_checker_allows_all(self):
        """permission_checker가 None이면 권한 검사 없음."""
        tm = TaskManager()
        t = tm.add_task("아무나", user_id="anyone")
        assert t is not None


# ── ProjectManager 권한 통합 테스트 ──

class TestProjectManagerPermissions:
    def test_admin_can_manage_project(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        p = pm.add_project("관리자 프로젝트", user_id=admin.id)
        pm.update_project(p.id, user_id=admin.id, name="수정됨")
        assert pm.get_project(p.id).name == "수정됨"

    def test_member_cannot_create_project(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        with pytest.raises(PermissionDeniedError):
            pm.add_project("멤버 프로젝트", user_id=member.id)

    def test_manager_can_create_project(self):
        um, pc, tm, pm, admin, manager, member, viewer = _make_system()
        p = pm.add_project("매니저 프로젝트", user_id=manager.id)
        assert p.name == "매니저 프로젝트"


# ── UserManager 권한 통합 테스트 ──

class TestUserManagerPermissions:
    def test_admin_can_manage_users(self):
        um = UserManager()
        admin = um.add_user("admin", "admin@test.com", role="admin")
        pc = PermissionChecker(um)
        um._permission_checker = pc
        new_user = um.add_user("new", "new@test.com", user_id=admin.id)
        assert new_user.username == "new"

    def test_manager_cannot_manage_users(self):
        um = UserManager()
        mgr = um.add_user("manager", "mgr@test.com", role="manager")
        pc = PermissionChecker(um)
        um._permission_checker = pc
        with pytest.raises(PermissionDeniedError):
            um.add_user("new", "new@test.com", user_id=mgr.id)


# ── 시스템 정책: 대소문자 무시 ──

class TestCaseInsensitivity:
    def test_search_tasks_case_insensitive(self):
        tm = TaskManager()
        tm.add_task("Login Bug Fix")
        tm.add_task("Dashboard feature")
        assert len(tm.search_tasks("LOGIN")) == 1
        assert len(tm.search_tasks("bug")) == 1

    def test_search_projects_case_insensitive(self):
        pm = ProjectManager()
        pm.add_project("Web Service")
        assert len(pm.search_projects("web")) == 1
        assert len(pm.search_projects("WEB")) == 1

    def test_get_user_by_username_case_insensitive(self):
        um = UserManager()
        um.add_user("Alice", "alice@test.com")
        u = um.get_user_by_username("ALICE")
        assert u.username == "Alice"

    def test_filter_tags_case_insensitive(self):
        tm = TaskManager()
        tm.add_task("A", tags=["Bug", "Urgent"])
        result = tm.filter_tasks(tags=["bug", "URGENT"])
        assert len(result) == 1


# ── 시스템 정책: 방어적 복사 ──

class TestDefensiveCopies:
    def test_list_tasks_defensive(self):
        tm = TaskManager()
        tm.add_task("A")
        tm.list_tasks().clear()
        assert tm.count == 1

    def test_list_projects_defensive(self):
        pm = ProjectManager()
        pm.add_project("A")
        pm.list_projects().clear()
        assert pm.count == 1

    def test_list_users_defensive(self):
        um = UserManager()
        um.add_user("a", "a@a.com")
        um.list_users().clear()
        assert um.count == 1

    def test_task_to_dict_defensive(self):
        from models import Task
        t = Task(id="t1", title="A", tags=["x"], metadata={"k": "v"})
        d = t.to_dict()
        d["tags"].append("hacked")
        d["metadata"]["hacked"] = True
        assert "hacked" not in t.tags
        assert "hacked" not in t.metadata

    def test_task_tags_defensive(self):
        from models import Task
        t = Task(id="t1", title="A", tags=["x"])
        tags = t.tags
        tags.append("hacked")
        assert len(t.tags) == 1

    def test_project_metadata_defensive(self):
        from models import Project
        p = Project(id="p1", name="A", metadata={"k": "v"})
        m = p.metadata
        m["hacked"] = True
        assert "hacked" not in p.metadata
