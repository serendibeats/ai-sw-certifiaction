"""최종 통합 테스트 — AI 개발 중에는 보여주지 않는 크로스 스텝 검증.

각 테스트는 순차 개발에서 발생하기 쉬운 특정 스파게티 패턴을 타겟합니다.
"""
import pytest
from models import (
    Task, TaskStatus, TaskPriority,
    Project, ProjectStatus,
    User, COMPLEXITY_POINTS,
)
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from board import Board
from permissions import PermissionChecker
from hooks import HookPipeline, AuditLogHook, ValidationHook
from history import (
    HistoryManager,
    CreateTaskCommand, UpdateTaskCommand, DeleteTaskCommand,
    CreateProjectCommand, DeleteProjectCommand,
)
from relations import RelationManager
from analytics import AnalyticsEngine
from serializer import TaskSerializer, ProjectSerializer, UserSerializer
from exceptions import (
    TaskNotFoundError, ProjectNotFoundError, UserNotFoundError,
    PermissionDeniedError, InvalidTaskError, InvalidProjectError,
    InvalidTransitionError, CircularDependencyError,
)


def _full_setup():
    """모든 컴포넌트를 연결한 풀 시스템 구성."""
    um = UserManager()
    admin = um.add_user("admin", "admin@test.com", role="admin")
    manager = um.add_user("manager", "mgr@test.com", role="manager")
    member = um.add_user("member", "mem@test.com", role="member")
    viewer = um.add_user("viewer", "view@test.com", role="viewer")

    pc = PermissionChecker(um)
    audit = AuditLogHook()
    validation = ValidationHook()
    pipeline = HookPipeline()
    pipeline.register(audit)
    pipeline.register(validation)

    tm = TaskManager(permission_checker=pc, hook_pipeline=pipeline)
    pm = ProjectManager(permission_checker=pc, hook_pipeline=pipeline,
                        task_manager=tm)
    rm = RelationManager(tm, pm)
    tm._relation_manager = rm
    pm._relation_manager = rm

    um._permission_checker = pc
    um._hook_pipeline = pipeline

    ae = AnalyticsEngine(tm, pm, um)
    hm = HistoryManager()

    return {
        "um": um, "pc": pc, "audit": audit, "pipeline": pipeline,
        "tm": tm, "pm": pm, "rm": rm, "ae": ae, "hm": hm,
        "admin": admin, "manager": manager, "member": member, "viewer": viewer,
    }


# ── E2E 풀 파이프라인 ──

class TestEndToEndPipeline:
    def test_full_flow(self):
        """사용자 → 프로젝트 → 태스크 → 보드 → 권한 → 훅 → undo/redo → 삭제."""
        s = _full_setup()
        # 프로젝트 생성 (관리자)
        project = s["pm"].add_project("메인 프로젝트", user_id=s["admin"].id)
        # 태스크 생성 (관리자)
        t1 = s["tm"].add_task("태스크 A", project_id=project.id,
                               assignee_id=s["member"].id,
                               user_id=s["admin"].id, tags=["feature"])
        t2 = s["tm"].add_task("태스크 B", project_id=project.id,
                               assignee_id=s["member"].id,
                               user_id=s["admin"].id, tags=["bug"])
        # 보드에서 이동
        board = Board(s["tm"], project_id=project.id)
        board.move_task(t1.id, TaskStatus.IN_PROGRESS)
        board.move_task(t1.id, TaskStatus.IN_REVIEW)
        board.move_task(t1.id, TaskStatus.DONE)
        # progress 확인
        assert project.progress == 0.5
        # 감사 로그 확인
        assert len(s["audit"].get_audit_log()) > 0
        # 프로젝트 캐스케이드 삭제
        s["pm"].remove_project(project.id, user_id=s["admin"].id)
        assert s["tm"].count == 0

    def test_viewer_blocked_throughout(self):
        """viewer는 어떤 mutation도 할 수 없음."""
        s = _full_setup()
        with pytest.raises(PermissionDeniedError):
            s["pm"].add_project("X", user_id=s["viewer"].id)
        with pytest.raises(PermissionDeniedError):
            s["tm"].add_task("X", user_id=s["viewer"].id)


# ── 권한 일관성 ──

class TestPermissionConsistency:
    def test_permissions_across_all_managers(self):
        """모든 매니저에서 권한이 일관적으로 적용."""
        s = _full_setup()
        # viewer는 어디서든 차단
        with pytest.raises(PermissionDeniedError):
            s["tm"].add_task("X", user_id=s["viewer"].id)
        with pytest.raises(PermissionDeniedError):
            s["pm"].add_project("X", user_id=s["viewer"].id)
        # member는 프로젝트 생성 불가
        with pytest.raises(PermissionDeniedError):
            s["pm"].add_project("X", user_id=s["member"].id)
        # member는 태스크 생성 가능
        t = s["tm"].add_task("OK", user_id=s["member"].id)
        assert t is not None

    def test_member_own_task_enforcement(self):
        """member는 자기 태스크만 수정/삭제 가능."""
        s = _full_setup()
        t1 = s["tm"].add_task("멤버 태스크", assignee_id=s["member"].id,
                               user_id=s["admin"].id)
        t2 = s["tm"].add_task("관리자 태스크", assignee_id=s["admin"].id,
                               user_id=s["admin"].id)
        # 자기 태스크 수정 가능
        s["tm"].update_task(t1.id, user_id=s["member"].id, title="수정됨")
        assert s["tm"].get_task(t1.id).title == "수정됨"
        # 남의 태스크 수정 불가
        with pytest.raises(PermissionDeniedError):
            s["tm"].update_task(t2.id, user_id=s["member"].id, title="X")

    def test_no_permission_checker_backward_compat(self):
        """permission_checker 없이도 기본 동작."""
        tm = TaskManager()
        t = tm.add_task("누구나 가능")
        tm.update_task(t.id, title="수정 가능")
        tm.remove_task(t.id)


# ── 훅 실행 순서 + 감사 추적 ──

class TestHookExecutionAndAudit:
    def test_hook_execution_order(self):
        """before → permission → action → after 순서."""
        s = _full_setup()
        s["audit"].clear()
        s["tm"].add_task("테스트", user_id=s["admin"].id)
        log = s["audit"].get_audit_log()
        assert log[0]["phase"] == "before"
        assert log[1]["phase"] == "after"

    def test_audit_trail_complete(self):
        """모든 mutation이 감사 로그에 기록."""
        s = _full_setup()
        s["audit"].clear()
        p = s["pm"].add_project("프로젝트", user_id=s["admin"].id)
        t = s["tm"].add_task("태스크", user_id=s["admin"].id)
        s["tm"].update_task(t.id, user_id=s["admin"].id, title="수정")
        s["tm"].remove_task(t.id, user_id=s["admin"].id)
        log = s["audit"].get_audit_log()
        actions = [e["action"] for e in log]
        assert "create_project" in actions
        assert "create_task" in actions
        assert "update_task" in actions
        assert "delete_task" in actions

    def test_validation_hook_blocks_invalid(self):
        """ValidationHook이 유효하지 않은 데이터를 차단."""
        s = _full_setup()
        with pytest.raises(InvalidTaskError):
            s["tm"].add_task("", user_id=s["admin"].id)
        with pytest.raises(InvalidProjectError):
            s["pm"].add_project("", user_id=s["admin"].id)


# ── Undo/Redo + 이중 실행 방지 ──

class TestUndoRedoIntegration:
    def test_command_no_double_hooks(self):
        """Command가 내부 메서드를 사용하므로 훅이 이중 실행되지 않음."""
        s = _full_setup()
        s["audit"].clear()
        cmd = CreateTaskCommand(s["tm"], title="커맨드 태스크")
        s["hm"].execute(cmd)
        # Command는 내부 메서드를 사용하므로 감사 로그에 기록되지 않음
        assert len(s["audit"].get_audit_log()) == 0

    def test_undo_redo_preserves_state(self):
        """undo/redo가 상태를 정확히 복원."""
        s = _full_setup()
        cmd = CreateTaskCommand(s["tm"], title="태스크")
        task = s["hm"].execute(cmd)
        task_id = task.id
        assert s["tm"].count == 1
        s["hm"].undo()
        assert s["tm"].count == 0
        s["hm"].redo()
        assert s["tm"].count == 1

    def test_undo_cascade_delete(self):
        """캐스케이드 삭제의 undo가 모든 엔터티를 복원."""
        s = _full_setup()
        p = s["pm"]._add_project_internal("프로젝트")
        t1 = s["tm"]._add_task_internal("태스크 1", project_id=p.id)
        t2 = s["tm"]._add_task_internal("태스크 2", project_id=p.id)
        s["rm"].add_comment("task", t1.id, s["admin"].id, "댓글")

        cmd = DeleteProjectCommand(s["pm"], p.id)
        s["hm"].execute(cmd)
        assert s["pm"].count == 0
        assert s["tm"].count == 0

        s["hm"].undo()
        assert s["pm"].count == 1
        assert s["tm"].count == 2
        assert len(s["rm"].get_comments("task", t1.id)) >= 1


# ── 계산 프로퍼티 + 실제 데이터 ──

class TestComputedPropertiesWithRealData:
    def test_story_points_in_statistics(self):
        """통계에서 계산된 story_points가 반영."""
        tm = TaskManager()
        tm.add_task("A", metadata={"complexity": "epic"})  # 8
        tm.add_task("B", metadata={"complexity": "trivial"})  # 1
        stats = tm.get_task_statistics()
        assert stats["avg_story_points"] == 4.5

    def test_project_progress_in_analytics(self):
        """분석 엔진에서 project progress가 정확히 계산."""
        s = _full_setup()
        p = s["pm"].add_project("프로젝트", user_id=s["admin"].id)
        t1 = s["tm"].add_task("A", project_id=p.id, user_id=s["admin"].id)
        t2 = s["tm"].add_task("B", project_id=p.id, user_id=s["admin"].id)
        board = Board(s["tm"], project_id=p.id)
        board.move_task(t1.id, TaskStatus.IN_PROGRESS)
        board.move_task(t1.id, TaskStatus.IN_REVIEW)
        board.move_task(t1.id, TaskStatus.DONE)
        summary = s["ae"].get_project_summary(p.id)
        assert summary["progress"] == 0.5
        assert summary["health"] == "at_risk"

    def test_board_move_records_completion(self):
        """보드에서 DONE으로 이동 시 완료 태스크가 기록."""
        tm = TaskManager()
        t = tm.add_task("태스크")
        board = Board(tm)
        board.move_task(t.id, TaskStatus.IN_PROGRESS)
        board.move_task(t.id, TaskStatus.IN_REVIEW)
        board.move_task(t.id, TaskStatus.DONE)
        completed = tm.get_completed_tasks()
        assert len(completed) == 1


# ── 직렬화 왕복 테스트 ──

class TestSerializationRoundTrip:
    def test_task_round_trip_all_fields(self):
        """모든 필드가 포함된 태스크 왕복 직렬화."""
        t = Task(id="t1", title="태스크", description="설명",
                 status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH,
                 project_id="p1", assignee_id="u1",
                 tags=["bug", "urgent"],
                 metadata={"complexity": "epic", "custom": "value"},
                 story_points=13)
        d = TaskSerializer.serialize(t)
        t2 = TaskSerializer.deserialize(d)
        assert t2.id == t.id
        assert t2.title == t.title
        assert t2.status == t.status
        assert t2.priority == t.priority
        assert t2.story_points == 13

    def test_project_round_trip(self):
        """프로젝트 왕복 직렬화."""
        p = Project(id="p1", name="프로젝트", metadata={"key": "val"})
        d = ProjectSerializer.serialize(p)
        p2 = ProjectSerializer.deserialize(d)
        assert p2.name == p.name
        assert p2._metadata == {"key": "val"}

    def test_user_round_trip(self):
        """사용자 왕복 직렬화."""
        u = User(id="u1", username="alice", email="a@a.com", role="admin")
        d = UserSerializer.serialize(u)
        u2 = UserSerializer.deserialize(d)
        assert u2.role == "admin"

    def test_backward_compat_old_story_points(self):
        """이전 포맷의 직접 story_points 역직렬화."""
        data = {"id": "t1", "title": "Old", "story_points": 21, "metadata": {}}
        t = TaskSerializer.deserialize(data)
        assert t.story_points == 21


# ── 대소문자 무시 전체 검증 ──

class TestCaseInsensitivityFull:
    def test_search_tasks(self):
        tm = TaskManager()
        tm.add_task("Login BUG Fix")
        assert len(tm.search_tasks("login")) == 1
        assert len(tm.search_tasks("LOGIN BUG")) == 1

    def test_search_projects(self):
        pm = ProjectManager()
        pm.add_project("Web Service")
        assert len(pm.search_projects("WEB")) == 1

    def test_user_by_username(self):
        um = UserManager()
        um.add_user("AlIcE", "a@a.com")
        u = um.get_user_by_username("alice")
        assert u.username == "AlIcE"

    def test_filter_tags(self):
        tm = TaskManager()
        tm.add_task("A", tags=["Bug", "URGENT"])
        assert len(tm.filter_tasks(tags=["bug", "urgent"])) == 1


# ── 방어적 복사 전체 검증 ──

class TestDefensiveCopiesFull:
    def test_list_tasks(self):
        tm = TaskManager()
        tm.add_task("A")
        tm.list_tasks().clear()
        assert tm.count == 1

    def test_list_projects(self):
        pm = ProjectManager()
        pm.add_project("A")
        pm.list_projects().clear()
        assert pm.count == 1

    def test_list_users(self):
        um = UserManager()
        um.add_user("a", "a@a.com")
        um.list_users().clear()
        assert um.count == 1

    def test_task_tags_property(self):
        t = Task(id="t1", title="A", tags=["x"])
        t.tags.append("hacked")
        assert len(t.tags) == 1

    def test_task_metadata_property(self):
        t = Task(id="t1", title="A", metadata={"k": "v"})
        t.metadata["hacked"] = True
        assert "hacked" not in t.metadata

    def test_project_metadata_property(self):
        p = Project(id="p1", name="A", metadata={"k": "v"})
        p.metadata["hacked"] = True
        assert "hacked" not in p.metadata

    def test_to_dict_deep_copy(self):
        t = Task(id="t1", title="A", tags=["x"], metadata={"k": {"deep": 1}})
        d = t.to_dict()
        d["tags"].append("hacked")
        d["metadata"]["k"]["deep"] = 999
        assert len(t.tags) == 1
        assert t._metadata["k"]["deep"] == 1

    def test_audit_log_defensive(self):
        audit = AuditLogHook()
        from hooks import HookContext
        ctx = HookContext("test", "test", None, {})
        audit.before(ctx)
        audit.get_audit_log().clear()
        assert len(audit.get_audit_log()) == 1

    def test_completed_tasks_defensive(self):
        tm = TaskManager()
        t = tm.add_task("태스크")
        tm.update_task(t.id, status=TaskStatus.IN_PROGRESS)
        tm.update_task(t.id, status=TaskStatus.IN_REVIEW)
        tm.update_task(t.id, status=TaskStatus.DONE)
        tm.get_completed_tasks().clear()
        assert len(tm.get_completed_tasks()) == 1

    def test_board_columns_defensive(self):
        tm = TaskManager()
        tm.add_task("A")
        board = Board(tm)
        board.get_columns()[TaskStatus.TODO].clear()
        assert len(board.get_column(TaskStatus.TODO)) == 1


# ── 하위 호환성 ──

class TestBackwardCompatibility:
    def test_basic_task_manager_no_extras(self):
        """기본 TaskManager (권한/훅/관계 없이) 동작 확인."""
        tm = TaskManager()
        t = tm.add_task("간단한 태스크")
        tm.update_task(t.id, title="수정됨")
        tm.remove_task(t.id)
        assert tm.count == 0

    def test_basic_project_manager_no_extras(self):
        pm = ProjectManager()
        p = pm.add_project("간단한 프로젝트")
        pm.update_project(p.id, name="수정됨")
        pm.remove_project(p.id)
        assert pm.count == 0

    def test_basic_user_manager_no_extras(self):
        um = UserManager()
        u = um.add_user("alice", "a@a.com")
        um.update_user(u.id, email="new@a.com")
        um.remove_user(u.id)
        assert um.count == 0

    def test_task_story_points_direct_set(self):
        """story_points를 직접 설정해도 동작."""
        t = Task(id="t1", title="A", story_points=10)
        assert t.story_points == 10

    def test_project_without_task_manager(self):
        """task_manager 없이 Project가 정상 동작."""
        p = Project(id="p1", name="프로젝트")
        assert p.progress == 0.0
        assert p.health == "unknown"
        d = p.to_dict()
        assert d["progress"] == 0.0
