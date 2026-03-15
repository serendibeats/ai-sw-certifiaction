"""Step 6: DLQ, fail-fast vs DLQ behavior, router DLQ."""
import pytest
from record import Record, RecordStatus
from processors import TransformProcessor, FilterProcessor
from pipeline import Pipeline
from router import Router
from dead_letter import DeadLetterQueue, DLQEntry
from errors import ProcessorError, RouterError


class TestDLQEntry:
    def test_dlq_entry_creation(self):
        r = Record(data={"x": 1})
        entry = DLQEntry(r, "test error", processor_name="TestProc")
        assert entry.record is r
        assert entry.error == "test error"
        assert entry.processor_name == "TestProc"
        assert entry.id is not None
        assert entry.timestamp > 0

    def test_dlq_entry_to_dict(self):
        r = Record(data={"x": 1})
        entry = DLQEntry(r, "err", processor_name="P")
        d = entry.to_dict()
        assert d["error"] == "err"
        assert d["processor_name"] == "P"


class TestDeadLetterQueue:
    def test_add_and_count(self):
        dlq = DeadLetterQueue()
        r = Record(data={"x": 1})
        dlq.add(r, "error1")
        assert dlq.count == 1

    def test_get_all_defensive_copy(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={"x": 1}), "error")
        entries = dlq.get_all()
        entries.clear()
        assert dlq.count == 1

    def test_get_by_processor(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={"x": 1}), "err1", processor_name="ProcA")
        dlq.add(Record(data={"x": 2}), "err2", processor_name="ProcB")
        dlq.add(Record(data={"x": 3}), "err3", processor_name="ProcA")
        results = dlq.get_by_processor("ProcA")
        assert len(results) == 2

    def test_get_by_processor_case_insensitive(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={"x": 1}), "err", processor_name="MyProcessor")
        results = dlq.get_by_processor("myprocessor")
        assert len(results) == 1

    def test_retry_removes_entry(self):
        dlq = DeadLetterQueue()
        r = Record(data={"x": 1})
        dlq.add(r, "error")
        entry = dlq.get_all()[0]
        record = dlq.retry(entry.id)
        assert record.id == r.id
        assert dlq.count == 0

    def test_retry_not_found(self):
        dlq = DeadLetterQueue()
        with pytest.raises(KeyError):
            dlq.retry("nonexistent")

    def test_clear(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={}), "err")
        dlq.add(Record(data={}), "err")
        dlq.clear()
        assert dlq.count == 0

    def test_max_size(self):
        dlq = DeadLetterQueue(max_size=3)
        for i in range(5):
            dlq.add(Record(data={"i": i}), f"error_{i}")
        assert dlq.count == 3


class TestPipelineFailFast:
    def test_fail_fast_without_dlq(self):
        def bad_transform(val):
            raise ProcessorError("TestProc", "r1", "intentional error")

        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("x", bad_transform))
        records = [Record(data={"x": "hello"})]
        with pytest.raises(ProcessorError):
            list(p.execute(records))

    def test_dlq_catches_errors(self):
        def bad_transform(val):
            raise ProcessorError("TestProc", "r1", "intentional error")

        dlq = DeadLetterQueue()
        p = Pipeline(name="test", dead_letter_queue=dlq)
        p.add_processor(TransformProcessor("x", bad_transform))
        records = [
            Record(data={"x": "hello"}),
            Record(data={"x": "world"}),
        ]
        results = list(p.execute(records))
        assert len(results) == 0
        assert dlq.count == 2

    def test_dlq_continues_processing_other_records(self):
        def maybe_fail(val):
            if val == "bad":
                raise ProcessorError("T", "r", "bad value")
            return val.upper()

        dlq = DeadLetterQueue()
        p = Pipeline(name="test", dead_letter_queue=dlq)
        p.add_processor(TransformProcessor("x", maybe_fail))
        records = [
            Record(data={"x": "good"}),
            Record(data={"x": "bad"}),
            Record(data={"x": "also_good"}),
        ]
        results = list(p.execute(records))
        assert len(results) == 2
        assert dlq.count == 1


class TestRouterDLQ:
    def test_router_no_match_without_dlq_raises(self):
        router = Router()
        router.add_route("only", Pipeline(), lambda r: r.get_field("type") == "X")
        r = Record(data={"type": "Y"})
        with pytest.raises(RouterError):
            router.route(r)

    def test_router_no_match_with_dlq(self):
        dlq = DeadLetterQueue()
        router = Router(dead_letter_queue=dlq)
        router.add_route("only", Pipeline(), lambda r: r.get_field("type") == "X")
        r = Record(data={"type": "Y"})
        result = router.route(r)
        assert result is None
        assert dlq.count == 1

    def test_router_batch_with_dlq(self):
        dlq = DeadLetterQueue()
        router = Router(dead_letter_queue=dlq)
        router.add_route("text", Pipeline(), lambda r: r.get_field("type") == "text")
        records = [
            Record(data={"type": "text"}),
            Record(data={"type": "unknown"}),
        ]
        result = router.route_batch(records)
        assert len(result.get("text", [])) == 1
        assert dlq.count == 1
