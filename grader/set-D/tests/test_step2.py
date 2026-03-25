"""Step 2: 칸반 보드 + 고급 필터링/정렬/통계 테스트."""
import pytest
from models import Task, TaskStatus, TaskPriority
from task_manager import TaskManager
from board import Board
from exceptions import InvalidTransitionError


class TestBoard:
    def _setup_board(self):
        tm = TaskManager()
        t1 = tm.add_task("태스크 1", project_id="p1")
        t2 = tm.add_task("태스크 2", project_id="p1")
        t3 = tm.add_task("태스크 3", project_id="p2")
        return tm, t1, t2, t3

    def test_get_columns(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        cols = board.get_columns()
        assert len(cols[TaskStatus.TODO]) == 3
        assert len(cols[TaskStatus.IN_PROGRESS]) == 0

    def test_get_columns_by_project(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm, project_id="p1")
        cols = board.get_columns()
        assert len(cols[TaskStatus.TODO]) == 2

    def test_get_column(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        assert len(board.get_column(TaskStatus.TODO)) == 3

    def test_move_task(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        board.move_task(t1.id, TaskStatus.IN_PROGRESS)
        assert t1.status == TaskStatus.IN_PROGRESS
        assert len(board.get_column(TaskStatus.IN_PROGRESS)) == 1

    def test_move_task_invalid(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        with pytest.raises(InvalidTransitionError):
            board.move_task(t1.id, TaskStatus.DONE)

    def test_wip_limit(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        board.set_wip_limit(TaskStatus.IN_PROGRESS, 2)
        assert board.check_wip_limit(TaskStatus.IN_PROGRESS) is True
        board.move_task(t1.id, TaskStatus.IN_PROGRESS)
        board.move_task(t2.id, TaskStatus.IN_PROGRESS)
        assert board.check_wip_limit(TaskStatus.IN_PROGRESS) is False

    def test_wip_count(self):
        tm, t1, t2, t3 = self._setup_board()
        board = Board(tm)
        assert board.get_wip_count(TaskStatus.TODO) == 3
        board.move_task(t1.id, TaskStatus.IN_PROGRESS)
        assert board.get_wip_count(TaskStatus.TODO) == 2
        assert board.get_wip_count(TaskStatus.IN_PROGRESS) == 1


class TestAdvancedFiltering:
    def _setup(self):
        tm = TaskManager()
        tm.add_task("버그 수정", priority=TaskPriority.HIGH,
                     assignee_id="u1", project_id="p1", tags=["bug", "urgent"])
        tm.add_task("기능 개발", priority=TaskPriority.MEDIUM,
                     assignee_id="u2", project_id="p1", tags=["feature"])
        tm.add_task("문서 작성", priority=TaskPriority.LOW,
                     assignee_id="u1", project_id="p2", tags=["docs"])
        tm.add_task("긴급 패치", priority=TaskPriority.CRITICAL,
                     assignee_id="u1", project_id="p1", tags=["bug", "hotfix"])
        return tm

    def test_filter_by_status(self):
        tm = self._setup()
        result = tm.filter_tasks(status=TaskStatus.TODO)
        assert len(result) == 4

    def test_filter_by_priority(self):
        tm = self._setup()
        result = tm.filter_tasks(priority=TaskPriority.HIGH)
        assert len(result) == 1

    def test_filter_by_assignee(self):
        tm = self._setup()
        result = tm.filter_tasks(assignee_id="u1")
        assert len(result) == 3

    def test_filter_by_project(self):
        tm = self._setup()
        result = tm.filter_tasks(project_id="p1")
        assert len(result) == 3

    def test_filter_by_tags(self):
        tm = self._setup()
        result = tm.filter_tasks(tags=["bug"])
        assert len(result) == 2

    def test_filter_combined(self):
        tm = self._setup()
        result = tm.filter_tasks(assignee_id="u1", tags=["bug"])
        assert len(result) == 2

    def test_filter_tags_case_insensitive(self):
        tm = self._setup()
        result = tm.filter_tasks(tags=["BUG"])
        assert len(result) == 2


class TestSorting:
    def test_sort_by_priority(self):
        tm = TaskManager()
        tm.add_task("Low", priority=TaskPriority.LOW)
        tm.add_task("Critical", priority=TaskPriority.CRITICAL)
        tm.add_task("Medium", priority=TaskPriority.MEDIUM)
        tasks = tm.list_tasks()
        sorted_tasks = tm.sort_tasks(tasks, key="priority")
        assert sorted_tasks[0].priority == TaskPriority.CRITICAL
        assert sorted_tasks[-1].priority == TaskPriority.LOW

    def test_sort_by_title(self):
        tm = TaskManager()
        tm.add_task("Banana")
        tm.add_task("Apple")
        tm.add_task("Cherry")
        tasks = tm.list_tasks()
        sorted_tasks = tm.sort_tasks(tasks, key="title")
        assert sorted_tasks[0].title == "Apple"

    def test_sort_by_story_points(self):
        tm = TaskManager()
        tm.add_task("A", story_points=5)
        tm.add_task("B", story_points=1)
        tm.add_task("C", story_points=3)
        tasks = tm.list_tasks()
        sorted_tasks = tm.sort_tasks(tasks, key="story_points")
        assert sorted_tasks[0].story_points == 1
        assert sorted_tasks[-1].story_points == 5


class TestStatistics:
    def test_basic_statistics(self):
        tm = TaskManager()
        tm.add_task("A", priority=TaskPriority.HIGH, story_points=5)
        tm.add_task("B", priority=TaskPriority.LOW, story_points=3)
        stats = tm.get_task_statistics()
        assert stats["total"] == 2
        assert stats["by_status"]["TODO"] == 2
        assert stats["by_priority"]["HIGH"] == 1
        assert stats["avg_story_points"] == 4.0

    def test_empty_statistics(self):
        tm = TaskManager()
        stats = tm.get_task_statistics()
        assert stats["total"] == 0
        assert stats["avg_story_points"] == 0.0
