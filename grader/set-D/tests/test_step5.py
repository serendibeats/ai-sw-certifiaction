"""Step 5: Undo/Redo + Command 패턴 테스트.

핵심: Command는 내부 메서드를 사용하므로 훅/권한이 이중 실행되지 않아야 합니다.
"""
import pytest
from models import TaskPriority, TaskStatus
from task_manager import TaskManager
from project_manager import ProjectManager
from hooks import HookPipeline, AuditLogHook, ValidationHook
from history import (
    HistoryManager,
    CreateTaskCommand, UpdateTaskCommand, DeleteTaskCommand,
    CreateProjectCommand, UpdateProjectCommand, DeleteProjectCommand,
)
from exceptions import TaskNotFoundError, ProjectNotFoundError


# ── HistoryManager 기본 테스트 ──

class TestHistoryManager:
    def test_execute_and_undo(self):
        tm = TaskManager()
        hm = HistoryManager()
        cmd = CreateTaskCommand(tm, title="태스크 1")
        task = hm.execute(cmd)
        assert tm.count == 1
        hm.undo()
        assert tm.count == 0

    def test_redo(self):
        tm = TaskManager()
        hm = HistoryManager()
        cmd = CreateTaskCommand(tm, title="태스크 1")
        hm.execute(cmd)
        hm.undo()
        assert tm.count == 0
        hm.redo()
        assert tm.count == 1

    def test_can_undo_can_redo(self):
        tm = TaskManager()
        hm = HistoryManager()
        assert hm.can_undo is False
        assert hm.can_redo is False
        cmd = CreateTaskCommand(tm, title="태스크")
        hm.execute(cmd)
        assert hm.can_undo is True
        assert hm.can_redo is False
        hm.undo()
        assert hm.can_undo is False
        assert hm.can_redo is True

    def test_new_execute_clears_redo(self):
        tm = TaskManager()
        hm = HistoryManager()
        hm.execute(CreateTaskCommand(tm, title="A"))
        hm.undo()
        assert hm.can_redo is True
        hm.execute(CreateTaskCommand(tm, title="B"))
        assert hm.can_redo is False

    def test_max_size(self):
        tm = TaskManager()
        hm = HistoryManager(max_size=3)
        for i in range(5):
            hm.execute(CreateTaskCommand(tm, title=f"태스크 {i}"))
        assert len(hm.get_history()) == 3

    def test_get_history(self):
        tm = TaskManager()
        hm = HistoryManager()
        hm.execute(CreateTaskCommand(tm, title="태스크 1"))
        hm.execute(CreateTaskCommand(tm, title="태스크 2"))
        history = hm.get_history()
        assert len(history) == 2
        assert "CreateTask" in history[0]


# ── CreateTaskCommand 테스트 ──

class TestCreateTaskCommand:
    def test_execute_creates_task(self):
        tm = TaskManager()
        cmd = CreateTaskCommand(tm, title="새 태스크",
                                 priority=TaskPriority.HIGH)
        task = cmd.execute()
        assert tm.count == 1
        assert task.priority == TaskPriority.HIGH

    def test_undo_removes_task(self):
        tm = TaskManager()
        cmd = CreateTaskCommand(tm, title="새 태스크")
        task = cmd.execute()
        cmd.undo()
        assert tm.count == 0


# ── UpdateTaskCommand 테스트 ──

class TestUpdateTaskCommand:
    def test_execute_updates_task(self):
        tm = TaskManager()
        task = tm._add_task_internal("원래 제목")
        cmd = UpdateTaskCommand(tm, task.id, title="변경됨")
        cmd.execute()
        assert tm.get_task(task.id).title == "변경됨"

    def test_undo_restores_task(self):
        tm = TaskManager()
        task = tm._add_task_internal("원래 제목")
        cmd = UpdateTaskCommand(tm, task.id, title="변경됨")
        cmd.execute()
        cmd.undo()
        assert tm.get_task(task.id).title == "원래 제목"


# ── DeleteTaskCommand 테스트 ──

class TestDeleteTaskCommand:
    def test_execute_deletes_task(self):
        tm = TaskManager()
        task = tm._add_task_internal("삭제될 태스크")
        cmd = DeleteTaskCommand(tm, task.id)
        cmd.execute()
        assert tm.count == 0

    def test_undo_restores_task(self):
        tm = TaskManager()
        task = tm._add_task_internal("삭제될 태스크")
        task_id = task.id
        cmd = DeleteTaskCommand(tm, task_id)
        cmd.execute()
        cmd.undo()
        assert tm.count == 1
        assert tm.get_task(task_id).title == "삭제될 태스크"


# ── 프로젝트 Command 테스트 ──

class TestProjectCommands:
    def test_create_project_command(self):
        pm = ProjectManager()
        cmd = CreateProjectCommand(pm, name="프로젝트")
        project = cmd.execute()
        assert pm.count == 1
        cmd.undo()
        assert pm.count == 0

    def test_update_project_command(self):
        pm = ProjectManager()
        project = pm._add_project_internal("원래 이름")
        cmd = UpdateProjectCommand(pm, project.id, name="변경됨")
        cmd.execute()
        assert pm.get_project(project.id).name == "변경됨"
        cmd.undo()
        assert pm.get_project(project.id).name == "원래 이름"

    def test_delete_project_command(self):
        pm = ProjectManager()
        project = pm._add_project_internal("삭제될 프로젝트")
        pid = project.id
        cmd = DeleteProjectCommand(pm, pid)
        cmd.execute()
        assert pm.count == 0
        cmd.undo()
        assert pm.count == 1


# ── 핵심: 이중 실행 방지 테스트 ──

class TestNoDoubleExecution:
    def test_create_task_command_no_double_hooks(self):
        """Command.execute()가 내부 메서드를 사용하므로 훅이 1회만 실행."""
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)

        # 공개 메서드로 태스크 추가 → 훅 2회 (before + after)
        tm.add_task("공개 메서드")
        assert len(audit.get_audit_log()) == 2
        audit.clear()

        # Command로 태스크 추가 → 훅 0회 (내부 메서드 사용)
        hm = HistoryManager()
        cmd = CreateTaskCommand(tm, title="커맨드")
        hm.execute(cmd)
        assert len(audit.get_audit_log()) == 0

    def test_undo_no_hooks(self):
        """undo가 내부 메서드를 사용하므로 훅이 실행되지 않음."""
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        hm = HistoryManager()

        cmd = CreateTaskCommand(tm, title="태스크")
        hm.execute(cmd)
        audit.clear()
        hm.undo()
        assert len(audit.get_audit_log()) == 0

    def test_redo_no_hooks(self):
        """redo가 내부 메서드를 사용하므로 훅이 실행되지 않음."""
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        hm = HistoryManager()

        cmd = CreateTaskCommand(tm, title="태스크")
        hm.execute(cmd)
        hm.undo()
        audit.clear()
        hm.redo()
        assert len(audit.get_audit_log()) == 0

    def test_update_command_no_double_hooks(self):
        """UpdateTaskCommand도 내부 메서드를 사용."""
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        task = tm._add_task_internal("태스크")
        audit.clear()

        hm = HistoryManager()
        cmd = UpdateTaskCommand(tm, task.id, title="변경")
        hm.execute(cmd)
        assert len(audit.get_audit_log()) == 0

    def test_delete_command_no_double_hooks(self):
        """DeleteTaskCommand도 내부 메서드를 사용."""
        audit = AuditLogHook()
        pipeline = HookPipeline()
        pipeline.register(audit)
        tm = TaskManager(hook_pipeline=pipeline)
        task = tm._add_task_internal("태스크")
        audit.clear()

        hm = HistoryManager()
        cmd = DeleteTaskCommand(tm, task.id)
        hm.execute(cmd)
        assert len(audit.get_audit_log()) == 0


# ── 복합 Undo/Redo 시나리오 ──

class TestComplexUndoRedo:
    def test_multiple_undo_redo(self):
        tm = TaskManager()
        hm = HistoryManager()
        t1 = hm.execute(CreateTaskCommand(tm, title="A"))
        t2 = hm.execute(CreateTaskCommand(tm, title="B"))
        assert tm.count == 2
        hm.undo()  # B 제거
        assert tm.count == 1
        hm.undo()  # A 제거
        assert tm.count == 0
        hm.redo()  # A 복원
        assert tm.count == 1
        hm.redo()  # B 복원
        assert tm.count == 2

    def test_undo_update_then_redo(self):
        tm = TaskManager()
        hm = HistoryManager()
        task = hm.execute(CreateTaskCommand(tm, title="원래"))
        hm.execute(UpdateTaskCommand(tm, task.id, title="변경"))
        assert tm.get_task(task.id).title == "변경"
        hm.undo()
        assert tm.get_task(task.id).title == "원래"
        hm.redo()
        assert tm.get_task(task.id).title == "변경"
