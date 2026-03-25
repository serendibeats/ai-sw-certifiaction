"""Step 4: 훅 파이프라인 + 감사/유효성 검증 테스트."""
import pytest
from models import TaskPriority
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from hooks import (
    Hook, HookContext, HookPipeline,
    AuditLogHook, ValidationHook,
)
from exceptions import InvalidTaskError, InvalidProjectError, InvalidUserError


# ── HookContext 테스트 ──

class TestHookContext:
    def test_context_creation(self):
        ctx = HookContext(
            action="create_task", entity_type="task",
            entity_id="t1", data={"title": "A"},
            user_id="u1",
        )
        assert ctx.action == "create_task"
        assert ctx.entity_type == "task"
        assert ctx.user_id == "u1"
        assert ctx.timestamp > 0


# ── AuditLogHook 테스트 ──

class TestAuditLogHook:
    def test_logs_before_and_after(self):
        hook = AuditLogHook()
        ctx = HookContext("create_task", "task", None, {"title": "A"})
        hook.before(ctx)
        ctx.entity_id = "t1"
        hook.after(ctx)
        log = hook.get_audit_log()
        assert len(log) == 2
        assert log[0]["phase"] == "before"
        assert log[1]["phase"] == "after"

    def test_clear_log(self):
        hook = AuditLogHook()
        ctx = HookContext("create_task", "task", None, {})
        hook.before(ctx)
        assert len(hook.get_audit_log()) == 1
        hook.clear()
        assert len(hook.get_audit_log()) == 0

    def test_audit_log_defensive_copy(self):
        hook = AuditLogHook()
        ctx = HookContext("create_task", "task", None, {})
        hook.before(ctx)
        hook.get_audit_log().clear()
        assert len(hook.get_audit_log()) == 1


# ── ValidationHook 테스트 ──

class TestValidationHook:
    def test_empty_task_title_raises(self):
        hook = ValidationHook()
        ctx = HookContext("create_task", "task", None, {"title": ""})
        with pytest.raises(InvalidTaskError):
            hook.before(ctx)

    def test_empty_project_name_raises(self):
        hook = ValidationHook()
        ctx = HookContext("create_project", "project", None, {"name": ""})
        with pytest.raises(InvalidProjectError):
            hook.before(ctx)

    def test_empty_username_raises(self):
        hook = ValidationHook()
        ctx = HookContext("create_user", "user", None, {"username": ""})
        with pytest.raises(InvalidUserError):
            hook.before(ctx)

    def test_valid_data_passes(self):
        hook = ValidationHook()
        ctx = HookContext("create_task", "task", None, {"title": "Valid"})
        result = hook.before(ctx)
        assert result is ctx


# ── HookPipeline 테스트 ──

class TestHookPipeline:
    def test_register_and_get_hooks(self):
        pipeline = HookPipeline()
        pipeline.register(AuditLogHook())
        pipeline.register(ValidationHook())
        names = pipeline.get_hooks()
        assert "AuditLogHook" in names
        assert "ValidationHook" in names

    def test_unregister(self):
        pipeline = HookPipeline()
        pipeline.register(AuditLogHook())
        pipeline.register(ValidationHook())
        pipeline.unregister("AuditLogHook")
        assert "AuditLogHook" not in pipeline.get_hooks()

    def test_execution_order(self):
        """훅이 등록 순서대로 실행됨."""
        order = []

        class HookA(Hook):
            @property
            def name(self):
                return "HookA"
            def before(self, ctx):
                order.append("A_before")
                return ctx
            def after(self, ctx):
                order.append("A_after")
                return ctx

        class HookB(Hook):
            @property
            def name(self):
                return "HookB"
            def before(self, ctx):
                order.append("B_before")
                return ctx
            def after(self, ctx):
                order.append("B_after")
                return ctx

        pipeline = HookPipeline()
        pipeline.register(HookA())
        pipeline.register(HookB())
        ctx = HookContext("test", "test", None, {})
        pipeline.execute_before(ctx)
        pipeline.execute_after(ctx)
        assert order == ["A_before", "B_before", "A_after", "B_after"]


# ── 매니저 통합 테스트 ──

class TestTaskManagerWithHooks:
    def test_audit_on_add_task(self):
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        tm.add_task("테스트")
        log = audit.get_audit_log()
        assert len(log) == 2  # before + after
        assert log[0]["action"] == "create_task"

    def test_audit_on_update_task(self):
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        t = tm.add_task("태스크")
        audit.clear()
        tm.update_task(t.id, title="수정됨")
        log = audit.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "update_task"

    def test_audit_on_remove_task(self):
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        t = tm.add_task("태스크")
        audit.clear()
        tm.remove_task(t.id)
        log = audit.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "delete_task"

    def test_validation_prevents_empty_title(self):
        pipeline = HookPipeline()
        pipeline.register(ValidationHook())
        tm = TaskManager(hook_pipeline=pipeline)
        with pytest.raises(InvalidTaskError):
            tm.add_task("")


class TestProjectManagerWithHooks:
    def test_audit_on_add_project(self):
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        pm = ProjectManager(hook_pipeline=pipeline)
        pm.add_project("프로젝트")
        log = audit.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "create_project"

    def test_validation_prevents_empty_name(self):
        pipeline = HookPipeline()
        pipeline.register(ValidationHook())
        pm = ProjectManager(hook_pipeline=pipeline)
        with pytest.raises(InvalidProjectError):
            pm.add_project("")


class TestUserManagerWithHooks:
    def test_audit_on_add_user(self):
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        um = UserManager(hook_pipeline=pipeline)
        um.add_user("alice", "alice@test.com")
        log = audit.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "create_user"

    def test_validation_prevents_empty_username(self):
        pipeline = HookPipeline()
        pipeline.register(ValidationHook())
        um = UserManager(hook_pipeline=pipeline)
        with pytest.raises(InvalidUserError):
            um.add_user("", "a@a.com")
