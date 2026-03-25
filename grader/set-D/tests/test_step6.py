"""Step 6: 엔터티 관계 + 캐스케이드 삭제 + 순환 의존성 테스트."""
import pytest
from task_manager import TaskManager
from project_manager import ProjectManager
from relations import RelationManager
from history import (
    HistoryManager, DeleteProjectCommand, CreateTaskCommand
)
from exceptions import (
    TaskNotFoundError, CircularDependencyError
)


def _setup_with_relations():
    """관계 매니저를 포함한 시스템 구성."""
    tm = TaskManager()
    pm = ProjectManager(task_manager=tm)
    rm = RelationManager(tm, pm)
    tm._relation_manager = rm
    pm._relation_manager = rm
    return tm, pm, rm


# ── 의존성 관리 테스트 ──

class TestDependencies:
    def test_add_dependency(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        rm.add_dependency(t1.id, t2.id)
        deps = rm.get_dependencies(t1.id)
        assert t2.id in deps

    def test_remove_dependency(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        rm.add_dependency(t1.id, t2.id)
        rm.remove_dependency(t1.id, t2.id)
        assert len(rm.get_dependencies(t1.id)) == 0

    def test_get_dependents(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        t3 = tm.add_task("태스크 3")
        rm.add_dependency(t2.id, t1.id)  # t2 depends on t1
        rm.add_dependency(t3.id, t1.id)  # t3 depends on t1
        dependents = rm.get_dependents(t1.id)
        assert len(dependents) == 2

    def test_circular_dependency_self(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        with pytest.raises(CircularDependencyError):
            rm.add_dependency(t1.id, t1.id)

    def test_circular_dependency_direct(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        rm.add_dependency(t1.id, t2.id)
        with pytest.raises(CircularDependencyError):
            rm.add_dependency(t2.id, t1.id)

    def test_circular_dependency_indirect(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        t3 = tm.add_task("태스크 3")
        rm.add_dependency(t1.id, t2.id)  # t1 → t2
        rm.add_dependency(t2.id, t3.id)  # t2 → t3
        with pytest.raises(CircularDependencyError):
            rm.add_dependency(t3.id, t1.id)  # t3 → t1 (순환!)

    def test_no_circular_when_valid(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        t3 = tm.add_task("태스크 3")
        rm.add_dependency(t1.id, t2.id)
        rm.add_dependency(t1.id, t3.id)  # t1 → t2, t1 → t3 (순환 아님)
        assert len(rm.get_dependencies(t1.id)) == 2


# ── 댓글 관리 테스트 ──

class TestComments:
    def test_add_comment(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        comment = rm.add_comment("task", t1.id, "u1", "좋은 진행입니다")
        assert comment["content"] == "좋은 진행입니다"
        assert comment["user_id"] == "u1"

    def test_get_comments(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        rm.add_comment("task", t1.id, "u1", "댓글 1")
        rm.add_comment("task", t1.id, "u2", "댓글 2")
        comments = rm.get_comments("task", t1.id)
        assert len(comments) == 2

    def test_remove_comments_for_entity(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        rm.add_comment("task", t1.id, "u1", "댓글")
        rm.remove_comments_for_entity("task", t1.id)
        assert len(rm.get_comments("task", t1.id)) == 0


# ── 캐스케이드 삭제 테스트 ──

class TestCascadeDelete:
    def test_task_delete_cleans_comments(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        rm.add_comment("task", t1.id, "u1", "댓글")
        tm.remove_task(t1.id)
        assert len(rm.get_comments("task", t1.id)) == 0

    def test_task_delete_cleans_dependencies(self):
        tm, pm, rm = _setup_with_relations()
        t1 = tm.add_task("태스크 1")
        t2 = tm.add_task("태스크 2")
        rm.add_dependency(t1.id, t2.id)
        tm.remove_task(t2.id)
        # t1의 의존성에서 t2가 제거됨
        assert t2.id not in rm.get_dependencies(t1.id)

    def test_project_delete_cascades_tasks(self):
        tm, pm, rm = _setup_with_relations()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("태스크 1", project_id=p.id)
        t2 = tm.add_task("태스크 2", project_id=p.id)
        t3 = tm.add_task("다른 프로젝트 태스크", project_id="other")
        pm.remove_project(p.id)
        assert tm.count == 1  # t3만 남음
        with pytest.raises(TaskNotFoundError):
            tm.get_task(t1.id)

    def test_project_delete_cascades_comments(self):
        tm, pm, rm = _setup_with_relations()
        p = pm.add_project("프로젝트")
        rm.add_comment("project", p.id, "u1", "프로젝트 댓글")
        t1 = tm.add_task("태스크", project_id=p.id)
        rm.add_comment("task", t1.id, "u1", "태스크 댓글")
        pm.remove_project(p.id)
        assert len(rm.get_comments("project", p.id)) == 0
        assert len(rm.get_comments("task", t1.id)) == 0


# ── 캐스케이드 Undo 테스트 ──

class TestCascadeUndo:
    def test_undo_project_delete_restores_tasks(self):
        tm, pm, rm = _setup_with_relations()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("태스크 1", project_id=p.id)
        t2 = tm.add_task("태스크 2", project_id=p.id)
        hm = HistoryManager()
        cmd = DeleteProjectCommand(pm, p.id)
        hm.execute(cmd)
        assert tm.count == 0
        assert pm.count == 0
        hm.undo()
        assert pm.count == 1
        assert tm.count == 2

    def test_undo_project_delete_restores_comments(self):
        tm, pm, rm = _setup_with_relations()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("태스크", project_id=p.id)
        rm.add_comment("task", t1.id, "u1", "댓글")
        rm.add_comment("project", p.id, "u1", "프로젝트 댓글")
        hm = HistoryManager()
        cmd = DeleteProjectCommand(pm, p.id)
        hm.execute(cmd)
        hm.undo()
        assert len(rm.get_comments("task", t1.id)) >= 1
        assert len(rm.get_comments("project", p.id)) >= 1
