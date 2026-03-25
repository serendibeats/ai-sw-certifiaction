"""Step 5: Lazy pipeline (generator behavior), priority routing, backward compat."""
import types
import pytest
from record import Record, RecordStatus, Schema
from processors import (
    TransformProcessor, FilterProcessor, EnrichProcessor, AggregateProcessor,
)
from pipeline import Pipeline
from router import Router


class TestLazyPipeline:
    def test_execute_returns_generator(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        records = [Record(data={"name": "alice"})]
        result = p.execute(records)
        assert hasattr(result, '__next__'), "execute() should return a generator"

    def test_lazy_evaluation_not_consumed_until_iterated(self):
        call_count = [0]

        def counting_transform(val):
            call_count[0] += 1
            return val.upper()

        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", counting_transform))
        records = [Record(data={"name": "alice"}), Record(data={"name": "bob"})]
        gen = p.execute(records)
        assert call_count[0] == 0, "Should not process until iterated"
        next(gen)
        assert call_count[0] == 1

    def test_lazy_with_list_materialization(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        records = [Record(data={"name": "a"}), Record(data={"name": "b"})]
        results = list(p.execute(records))
        assert len(results) == 2

    def test_execute_accepts_generator_input(self):
        def record_gen():
            for name in ["alice", "bob"]:
                yield Record(data={"name": name})

        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        results = list(p.execute(record_gen()))
        assert len(results) == 2
        assert results[0].get_field("name") == "ALICE"

    def test_execute_eager_returns_list(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        records = [Record(data={"name": "alice"})]
        results = p.execute_eager(records)
        assert isinstance(results, list)
        assert results[0].get_field("name") == "ALICE"

    def test_lazy_property_default_true(self):
        p = Pipeline()
        assert p.lazy is True

    def test_non_lazy_returns_list(self):
        p = Pipeline(name="test")
        p.lazy = False
        p.add_processor(TransformProcessor("name", str.upper))
        records = [Record(data={"name": "alice"})]
        result = p.execute(records)
        assert isinstance(result, list)

    def test_aggregate_with_lazy(self):
        p = Pipeline(name="test")
        p.add_processor(AggregateProcessor("cat", "val"))
        records = [
            Record(data={"cat": "A", "val": 10}),
            Record(data={"cat": "A", "val": 20}),
        ]
        results = list(p.execute(records))
        assert len(results) == 1
        assert results[0].get_field("val") == 30

    def test_filter_with_lazy(self):
        p = Pipeline(name="test")
        p.add_processor(FilterProcessor(lambda r: r.get_field("keep") is True))
        records = [
            Record(data={"keep": True, "name": "A"}),
            Record(data={"keep": False, "name": "B"}),
            Record(data={"keep": True, "name": "C"}),
        ]
        results = list(p.execute(records))
        assert len(results) == 2

    def test_execute_eager_backward_compat(self):
        p = Pipeline(name="test")
        records = [Record(data={"x": i}) for i in range(5)]
        results = p.execute_eager(records)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_chained_processors_lazy(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("val", lambda v: v * 2))
        p.add_processor(EnrichProcessor("doubled", lambda r: True))
        records = [Record(data={"val": 5})]
        results = list(p.execute(records))
        assert results[0].get_field("val") == 10
        assert results[0].get_field("doubled") is True


class TestPriorityRouting:
    def test_priority_highest_first(self):
        router = Router()
        router.add_route("low", Pipeline(), lambda r: True, priority=1)
        router.add_route("high", Pipeline(), lambda r: True, priority=10)
        r = Record(data={})
        assert router.route(r) == "high"

    def test_priority_with_conditions(self):
        router = Router()
        router.add_route("general", Pipeline(), lambda r: True, priority=1)
        router.add_route(
            "premium", Pipeline(),
            lambda r: r.get_field("tier") == "premium",
            priority=10,
        )
        regular = Record(data={"tier": "regular"})
        premium = Record(data={"tier": "premium"})
        assert router.route(regular) == "general"
        assert router.route(premium) == "premium"

    def test_priority_batch_routing(self):
        router = Router()
        router.add_route("low", Pipeline(), lambda r: True, priority=1)
        router.add_route(
            "high", Pipeline(),
            lambda r: r.get_field("priority") == "high",
            priority=10,
        )
        records = [
            Record(data={"priority": "high"}),
            Record(data={"priority": "low"}),
            Record(data={"priority": "high"}),
        ]
        result = router.route_batch(records)
        assert len(result.get("high", [])) == 2
        assert len(result.get("low", [])) == 1

    def test_default_priority_zero(self):
        router = Router()
        router.add_route("a", Pipeline(), lambda r: True)
        router.add_route("b", Pipeline(), lambda r: True, priority=1)
        r = Record(data={})
        assert router.route(r) == "b"

    def test_equal_priority_both_match(self):
        router = Router()
        router.add_route("a", Pipeline(), lambda r: True, priority=5)
        router.add_route("b", Pipeline(), lambda r: True, priority=5)
        r = Record(data={})
        name = router.route(r)
        assert name in ["a", "b"]

    def test_priority_negative(self):
        router = Router()
        router.add_route("low_priority", Pipeline(), lambda r: True, priority=-10)
        router.add_route("normal", Pipeline(), lambda r: True, priority=0)
        r = Record(data={})
        assert router.route(r) == "normal"

    def test_priority_routing_with_multiple_conditions(self):
        router = Router()
        router.add_route("catch_all", Pipeline(), lambda r: True, priority=0)
        router.add_route(
            "type_a", Pipeline(),
            lambda r: r.get_field("type") == "A",
            priority=5,
        )
        router.add_route(
            "urgent_type_a", Pipeline(),
            lambda r: r.get_field("type") == "A" and r.get_field("urgent") is True,
            priority=10,
        )
        urgent_a = Record(data={"type": "A", "urgent": True})
        normal_a = Record(data={"type": "A", "urgent": False})
        other = Record(data={"type": "B"})
        assert router.route(urgent_a) == "urgent_type_a"
        assert router.route(normal_a) == "type_a"
        assert router.route(other) == "catch_all"
