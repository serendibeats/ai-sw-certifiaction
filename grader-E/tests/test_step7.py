"""Step 7: MetricsCollector, record immutability, processor adaptation."""
import time
import pytest
from record import Record, RecordStatus, Schema
from processors import TransformProcessor, EnrichProcessor, FilterProcessor
from pipeline import Pipeline
from metrics import MetricsCollector
from dead_letter import DeadLetterQueue
from errors import ProcessorError


class TestMetricsCollector:
    def test_record_processing(self):
        mc = MetricsCollector()
        mc.record_processing("proc1", 10.0, True)
        mc.record_processing("proc1", 20.0, True)
        mc.record_processing("proc1", 5.0, False)
        metrics = mc.get_processor_metrics("proc1")
        assert metrics["total"] == 3
        assert metrics["success"] == 2
        assert metrics["failed"] == 1

    def test_avg_duration(self):
        mc = MetricsCollector()
        mc.record_processing("proc1", 10.0, True)
        mc.record_processing("proc1", 20.0, True)
        metrics = mc.get_processor_metrics("proc1")
        assert metrics["avg_duration"] == 15.0

    def test_get_all_metrics(self):
        mc = MetricsCollector()
        mc.record_processing("proc1", 10.0, True)
        mc.record_processing("proc2", 20.0, False)
        all_metrics = mc.get_all_metrics()
        assert "proc1" in all_metrics
        assert "proc2" in all_metrics

    def test_pipeline_metrics(self):
        mc = MetricsCollector()
        mc.record_pipeline_execution("pipeline1", 100, 500.0, 95, 5)
        metrics = mc.get_pipeline_metrics("pipeline1")
        assert metrics["total_records"] == 100
        assert metrics["success"] == 95
        assert metrics["failed"] == 5
        assert metrics["execution_count"] == 1

    def test_multiple_pipeline_executions(self):
        mc = MetricsCollector()
        mc.record_pipeline_execution("p1", 50, 200.0, 48, 2)
        mc.record_pipeline_execution("p1", 30, 100.0, 30, 0)
        metrics = mc.get_pipeline_metrics("p1")
        assert metrics["total_records"] == 80
        assert metrics["execution_count"] == 2

    def test_get_empty_metrics(self):
        mc = MetricsCollector()
        metrics = mc.get_processor_metrics("nonexistent")
        assert metrics["total"] == 0
        assert metrics["avg_duration"] == 0.0

    def test_reset(self):
        mc = MetricsCollector()
        mc.record_processing("proc1", 10.0, True)
        mc.record_pipeline_execution("p1", 10, 100.0, 10, 0)
        mc.reset()
        assert mc.get_processor_metrics("proc1")["total"] == 0
        assert mc.get_pipeline_metrics("p1")["execution_count"] == 0


class TestRecordImmutability:
    def test_set_field_returns_new_record(self):
        r = Record(data={"name": "Alice"})
        r2 = r.set_field("name", "Bob")
        assert r.get_field("name") == "Alice"
        assert r2.get_field("name") == "Bob"
        assert r is not r2

    def test_set_field_preserves_id(self):
        r = Record(data={"x": 1})
        r2 = r.set_field("x", 2)
        assert r2.id == r.id

    def test_set_field_preserves_metadata(self):
        r = Record(data={"x": 1}, metadata={"key": "val"})
        r2 = r.set_field("x", 2)
        assert r2.metadata["key"] == "val"

    def test_set_field_deep_copy_data(self):
        r = Record(data={"items": [1, 2, 3]})
        r2 = r.set_field("items", [4, 5])
        assert r.get_field("items") == [1, 2, 3]
        assert r2.get_field("items") == [4, 5]

    def test_copy_method(self):
        r = Record(data={"x": [1, 2]}, metadata={"m": "v"})
        r2 = r.copy()
        r2.data["x"].append(3)
        r2.metadata["m"] = "changed"
        assert r.data["x"] == [1, 2]
        assert r.metadata["m"] == "v"

    def test_set_field_updates_timestamp(self):
        r = Record(data={"x": 1})
        old_ts = r.updated_at
        time.sleep(0.01)
        r2 = r.set_field("x", 2)
        assert r2.updated_at >= old_ts


class TestProcessorAdaptation:
    def test_transform_captures_set_field_return(self):
        r = Record(data={"name": "alice"})
        tp = TransformProcessor("name", str.upper)
        result = tp.process(r)
        assert result.get_field("name") == "ALICE"
        assert r.get_field("name") == "alice"  # original unchanged

    def test_enrich_captures_set_field_return(self):
        r = Record(data={"x": 10})
        ep = EnrichProcessor("doubled", lambda rec: rec.get_field("x", 0) * 2)
        result = ep.process(r)
        assert result.get_field("doubled") == 20
        assert r.get_field("doubled") is None  # original unchanged

    def test_pipeline_immutability_throughout(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        p.add_processor(EnrichProcessor("greeting", lambda r: f"Hi {r.get_field('name')}"))
        original = Record(data={"name": "alice"})
        results = list(p.execute([original]))
        assert original.get_field("name") == "alice"
        assert results[0].get_field("name") == "ALICE"
        assert results[0].get_field("greeting") == "Hi ALICE"


class TestPipelineMetricsIntegration:
    def test_pipeline_records_processor_metrics(self):
        mc = MetricsCollector()
        p = Pipeline(name="test", metrics_collector=mc)
        p.add_processor(TransformProcessor("name", str.upper, name="upper"))
        records = [Record(data={"name": "alice"}), Record(data={"name": "bob"})]
        list(p.execute(records))
        metrics = mc.get_processor_metrics("upper")
        assert metrics["total"] == 2
        assert metrics["success"] == 2

    def test_pipeline_records_failure_metrics(self):
        def bad_fn(val):
            raise ProcessorError("bad", "r", "fail")

        mc = MetricsCollector()
        dlq = DeadLetterQueue()
        p = Pipeline(name="test", metrics_collector=mc, dead_letter_queue=dlq)
        p.add_processor(TransformProcessor("x", bad_fn, name="bad_proc"))
        records = [Record(data={"x": "val"})]
        list(p.execute(records))
        metrics = mc.get_processor_metrics("bad_proc")
        assert metrics["failed"] == 1

    def test_pipeline_records_pipeline_metrics(self):
        mc = MetricsCollector()
        p = Pipeline(name="my_pipeline", metrics_collector=mc)
        p.add_processor(TransformProcessor("x", str.upper))
        records = [Record(data={"x": "a"}), Record(data={"x": "b"})]
        list(p.execute(records))
        metrics = mc.get_pipeline_metrics("my_pipeline")
        assert metrics["total_records"] == 2

    def test_metrics_without_collector(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("x", str.upper))
        records = [Record(data={"x": "a"})]
        results = list(p.execute(records))
        assert len(results) == 1  # works fine without metrics
