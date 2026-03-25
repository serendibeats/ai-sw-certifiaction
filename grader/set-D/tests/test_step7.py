"""Step 7: 계산 프로퍼티 + 분석 엔진 테스트."""
import time
import pytest
from models import Task, TaskStatus, TaskPriority, Project, COMPLEXITY_POINTS
from task_manager import TaskManager
from project_manager import ProjectManager
from user_manager import UserManager
from analytics import AnalyticsEngine
from board import Board


# ── story_points 계산 프로퍼티 테스트 ──

class TestStoryPointsComputed:
    def test_default_story_points(self):
        """기본 complexity는 medium → 3."""
        t = Task(id="t1", title="태스크")
        assert t.story_points == 3

    def test_complexity_based_points(self):
        """metadata.complexity에 따른 포인트 계산."""
        t = Task(id="t1", title="태스크", metadata={"complexity": "epic"})
        assert t.story_points == 8
        t2 = Task(id="t2", title="태스크", metadata={"complexity": "trivial"})
        assert t2.story_points == 1

    def test_explicit_override(self):
        """metadata에 명시적 story_points가 있으면 우선."""
        t = Task(id="t1", title="태스크",
                 metadata={"complexity": "epic", "story_points": 13})
        assert t.story_points == 13

    def test_story_points_setter(self):
        """story_points 세터를 통한 설정."""
        t = Task(id="t1", title="태스크")
        t.story_points = 5
        assert t.story_points == 5
        # metadata에 저장됨
        assert t._metadata["story_points"] == 5

    def test_constructor_story_points(self):
        """생성자에서 story_points를 직접 지정."""
        t = Task(id="t1", title="태스크", story_points=8)
        assert t.story_points == 8

    def test_backward_compat_story_points_in_to_dict(self):
        """to_dict()에 story_points가 포함됨."""
        t = Task(id="t1", title="태스크", story_points=5)
        d = t.to_dict()
        assert d["story_points"] == 5

    def test_all_complexity_levels(self):
        for complexity, expected in COMPLEXITY_POINTS.items():
            t = Task(id="t", title="T", metadata={"complexity": complexity})
            assert t.story_points == expected


# ── Project progress/health 테스트 ──

class TestProjectComputed:
    def test_progress_no_task_manager(self):
        p = Project(id="p1", name="프로젝트")
        assert p.progress == 0.0

    def test_health_no_task_manager(self):
        p = Project(id="p1", name="프로젝트")
        assert p.health == "unknown"

    def test_progress_with_tasks(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("A", project_id=p.id)
        t2 = tm.add_task("B", project_id=p.id)
        # 0/2 = 0.0
        assert p.progress == 0.0
        # Move t1 to DONE
        t1.transition_to(TaskStatus.IN_PROGRESS)
        t1.transition_to(TaskStatus.IN_REVIEW)
        t1.transition_to(TaskStatus.DONE)
        # 1/2 = 0.5
        assert p.progress == 0.5

    def test_health_critical(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        p = pm.add_project("프로젝트")
        tm.add_task("A", project_id=p.id)
        tm.add_task("B", project_id=p.id)
        # 0/2 → progress 0.0 → critical
        assert p.health == "critical"

    def test_health_at_risk(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("A", project_id=p.id)
        tm.add_task("B", project_id=p.id)
        t1.transition_to(TaskStatus.IN_PROGRESS)
        t1.transition_to(TaskStatus.IN_REVIEW)
        t1.transition_to(TaskStatus.DONE)
        # 1/2 = 0.5 → at_risk
        assert p.health == "at_risk"

    def test_health_healthy(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        p = pm.add_project("프로젝트")
        tasks = []
        for i in range(10):
            tasks.append(tm.add_task(f"태스크 {i}", project_id=p.id))
        # 7/10 DONE
        for t in tasks[:7]:
            t.transition_to(TaskStatus.IN_PROGRESS)
            t.transition_to(TaskStatus.IN_REVIEW)
            t.transition_to(TaskStatus.DONE)
        assert p.health == "healthy"

    def test_progress_empty_project(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        p = pm.add_project("빈 프로젝트")
        assert p.progress == 0.0


# ── AnalyticsEngine 테스트 ──

class TestAnalyticsEngine:
    def _setup(self):
        tm = TaskManager()
        pm = ProjectManager(task_manager=tm)
        um = UserManager()
        ae = AnalyticsEngine(tm, pm, um)
        return tm, pm, um, ae

    def test_workload_distribution(self):
        tm, pm, um, ae = self._setup()
        tm.add_task("A", assignee_id="u1")
        tm.add_task("B", assignee_id="u1")
        tm.add_task("C", assignee_id="u2")
        dist = ae.get_workload_distribution()
        assert dist["u1"] == 2
        assert dist["u2"] == 1

    def test_project_summary(self):
        tm, pm, um, ae = self._setup()
        p = pm.add_project("프로젝트")
        tm.add_task("A", project_id=p.id)
        tm.add_task("B", project_id=p.id)
        summary = ae.get_project_summary(p.id)
        assert summary["name"] == "프로젝트"
        assert summary["total_tasks"] == 2
        assert "TODO" in summary["by_status"]

    def test_velocity(self):
        tm, pm, um, ae = self._setup()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("A", project_id=p.id, story_points=5)
        # 태스크를 DONE으로 전이
        t1.transition_to(TaskStatus.IN_PROGRESS)
        t1.transition_to(TaskStatus.IN_REVIEW)
        t1.transition_to(TaskStatus.DONE)
        tm._record_completion(t1)
        velocity = ae.get_velocity(p.id, days=7)
        assert velocity["completed_count"] == 1
        assert velocity["completed_points"] == 5

    def test_team_report(self):
        tm, pm, um, ae = self._setup()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("A", project_id=p.id, assignee_id="u1")
        t2 = tm.add_task("B", project_id=p.id, assignee_id="u1")
        t3 = tm.add_task("C", project_id=p.id, assignee_id="u2")
        t1.transition_to(TaskStatus.IN_PROGRESS)
        t1.transition_to(TaskStatus.IN_REVIEW)
        t1.transition_to(TaskStatus.DONE)
        report = ae.get_team_report(p.id)
        assert report["members"]["u1"]["assigned"] == 2
        assert report["members"]["u1"]["completed"] == 1
        assert report["members"]["u2"]["assigned"] == 1

    def test_burndown_data(self):
        tm, pm, um, ae = self._setup()
        p = pm.add_project("프로젝트")
        t1 = tm.add_task("A", project_id=p.id)
        t2 = tm.add_task("B", project_id=p.id)
        t1.transition_to(TaskStatus.IN_PROGRESS)
        t1.transition_to(TaskStatus.IN_REVIEW)
        t1.transition_to(TaskStatus.DONE)
        tm._record_completion(t1)
        data = ae.get_burndown_data(p.id)
        assert len(data) >= 1
        # 마지막 항목의 remaining은 현재 미완료 수
        assert data[-1]["remaining"] == 1
