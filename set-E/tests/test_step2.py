"""Step 2: Processors and Pipeline basics tests."""
import pytest
from record import Record, RecordStatus, Schema
from processors import (
    Processor, FilterProcessor, TransformProcessor,
    EnrichProcessor, AggregateProcessor,
)
from pipeline import Pipeline
from errors import ProcessorError


class TestFilterProcessor:
    def test_filter_pass(self):
        r = Record(data={"status": "active"})
        fp = FilterProcessor(lambda rec: rec.get_field("status") == "active")
        result = fp.process(r)
        assert result is not None
        assert result.id == r.id

    def test_filter_reject(self):
        r = Record(data={"status": "inactive"})
        fp = FilterProcessor(lambda rec: rec.get_field("status") == "active")
        result = fp.process(r)
        assert result is None

    def test_filter_name(self):
        fp = FilterProcessor(lambda r: True, name="MyFilter")
        assert fp.name == "MyFilter"


class TestTransformProcessor:
    def test_transform_field(self):
        r = Record(data={"name": "alice"})
        tp = TransformProcessor("name", str.upper)
        result = tp.process(r)
        assert result.get_field("name") == "ALICE"

    def test_transform_preserves_other_fields(self):
        r = Record(data={"name": "alice", "age": 30})
        tp = TransformProcessor("name", str.upper)
        result = tp.process(r)
        assert result.get_field("age") == 30

    def test_transform_missing_field_skips(self):
        r = Record(data={"age": 30})
        tp = TransformProcessor("name", str.upper)
        result = tp.process(r)
        assert result.get_field("name") is None
        assert result.get_field("age") == 30

    def test_transform_returns_new_record(self):
        r = Record(data={"name": "alice"})
        tp = TransformProcessor("name", str.upper)
        result = tp.process(r)
        assert r.get_field("name") == "alice"  # original unchanged


class TestEnrichProcessor:
    def test_enrich_adds_field(self):
        r = Record(data={"first": "Alice", "last": "Smith"})
        ep = EnrichProcessor(
            "full_name",
            lambda rec: f"{rec.get_field('first', '')} {rec.get_field('last', '')}",
        )
        result = ep.process(r)
        assert result.get_field("full_name") == "Alice Smith"

    def test_enrich_returns_new_record(self):
        r = Record(data={"x": 1})
        ep = EnrichProcessor("y", lambda rec: rec.get_field("x", 0) * 2)
        result = ep.process(r)
        assert r.get_field("y") is None  # original unchanged
        assert result.get_field("y") == 2

    def test_enrich_sets_enriched_status(self):
        r = Record(data={"x": 1})
        ep = EnrichProcessor("y", lambda rec: 42)
        result = ep.process(r)
        assert result.status == RecordStatus.ENRICHED


class TestAggregateProcessor:
    def test_aggregate_sum(self):
        ap = AggregateProcessor("category", "amount", agg_fn="sum")
        ap.process(Record(data={"category": "A", "amount": 10}))
        ap.process(Record(data={"category": "A", "amount": 20}))
        ap.process(Record(data={"category": "B", "amount": 5}))
        results = ap.get_results()
        assert len(results) == 2
        amounts = {r.get_field("category"): r.get_field("amount") for r in results}
        assert amounts["A"] == 30
        assert amounts["B"] == 5

    def test_aggregate_count(self):
        ap = AggregateProcessor("type", "value", agg_fn="count")
        ap.process(Record(data={"type": "X", "value": 1}))
        ap.process(Record(data={"type": "X", "value": 2}))
        results = ap.get_results()
        assert results[0].get_field("value") == 2

    def test_aggregate_reset(self):
        ap = AggregateProcessor("cat", "val", agg_fn="sum")
        ap.process(Record(data={"cat": "A", "val": 10}))
        ap.reset()
        results = ap.get_results()
        assert len(results) == 0

    def test_aggregate_process_returns_none(self):
        ap = AggregateProcessor("cat", "val")
        result = ap.process(Record(data={"cat": "A", "val": 10}))
        assert result is None


class TestPipeline:
    def test_pipeline_basic_execution(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        records = [Record(data={"name": "alice"}), Record(data={"name": "bob"})]
        results = list(p.execute(records))
        assert len(results) == 2
        assert results[0].get_field("name") == "ALICE"
        assert results[1].get_field("name") == "BOB"

    def test_pipeline_filter_drops_records(self):
        p = Pipeline(name="test")
        p.add_processor(FilterProcessor(lambda r: r.get_field("active") is True))
        records = [
            Record(data={"name": "A", "active": True}),
            Record(data={"name": "B", "active": False}),
            Record(data={"name": "C", "active": True}),
        ]
        results = list(p.execute(records))
        assert len(results) == 2

    def test_pipeline_chaining(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        p.add_processor(EnrichProcessor("greeting", lambda r: f"Hello {r.get_field('name')}"))
        records = [Record(data={"name": "alice"})]
        results = list(p.execute(records))
        assert results[0].get_field("greeting") == "Hello ALICE"

    def test_pipeline_aggregate(self):
        p = Pipeline(name="test")
        p.add_processor(AggregateProcessor("category", "amount"))
        records = [
            Record(data={"category": "A", "amount": 10}),
            Record(data={"category": "A", "amount": 20}),
        ]
        results = list(p.execute(records))
        assert len(results) == 1
        assert results[0].get_field("amount") == 30

    def test_pipeline_add_returns_self(self):
        p = Pipeline()
        result = p.add_processor(TransformProcessor("x", str.upper))
        assert result is p

    def test_pipeline_get_processors(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("name", str.upper, name="upper"))
        p.add_processor(FilterProcessor(lambda r: True, name="passthrough"))
        names = p.get_processors()
        assert "upper" in names
        assert "passthrough" in names

    def test_pipeline_remove_processor(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("name", str.upper, name="upper"))
        p.remove_processor("upper")
        assert len(p.get_processors()) == 0

    def test_pipeline_execution_count(self):
        p = Pipeline()
        assert p.get_execution_count() == 0
        list(p.execute([]))
        assert p.get_execution_count() == 1
        list(p.execute([]))
        assert p.get_execution_count() == 2

    def test_pipeline_empty_processors(self):
        p = Pipeline()
        records = [Record(data={"x": 1})]
        results = list(p.execute(records))
        assert len(results) == 1
        assert results[0].get_field("x") == 1

    def test_pipeline_name(self):
        p = Pipeline(name="my_pipeline")
        assert p.name == "my_pipeline"
