"""Final integration tests -- NOT shown to AI during development.

Tests cross-step interactions across all 8 steps.
Each test targets a specific spaghetti pattern from sequential development.
"""
import time
import pytest
from record import Record, RecordStatus, Schema
from validators import (
    RequiredFieldValidator, TypeValidator, RangeValidator, CompositeValidator,
)
from serializer import RecordSerializer
from processors import (
    TransformProcessor, FilterProcessor, EnrichProcessor, AggregateProcessor,
)
from pipeline import Pipeline
from router import Router
from registry import PipelineRegistry
from schema_registry import SchemaRegistry, SchemaMigrator
from dead_letter import DeadLetterQueue
from metrics import MetricsCollector
from reports import ReportGenerator
from errors import ProcessorError, RouterError


# --- Helpers ---

def _make_schema_v1():
    return Schema(name="event", version=1, fields={
        "type": {"type": "str", "required": True, "default": None},
        "value": {"type": "number", "required": True, "default": None},
        "source": {"type": "str", "required": False, "default": "unknown"},
    })


def _make_schema_v2():
    return Schema(name="event", version=2, fields={
        "type": {"type": "str", "required": True, "default": None},
        "value": {"type": "number", "required": True, "default": None},
        "source": {"type": "str", "required": False, "default": "unknown"},
        "priority": {"type": "int", "required": False, "default": 0},
        "tags": {"type": "list", "required": False, "default": []},
    })


def _make_records(n=10, schema=None):
    records = []
    for i in range(n):
        records.append(Record(
            data={
                "type": "metric" if i % 2 == 0 else "log",
                "value": (i + 1) * 10,
                "source": "sensor_a" if i < 5 else "sensor_b",
            },
            schema=schema,
            source="test",
        ))
    return records


# --- E2E Full Pipeline ---

class TestEndToEndPipeline:
    def test_full_flow_create_validate_route_process_aggregate_report(self):
        mc = MetricsCollector()
        dlq = DeadLetterQueue()

        # Create pipelines
        metric_pipeline = Pipeline(name="metrics", metrics_collector=mc, dead_letter_queue=dlq)
        metric_pipeline.add_processor(
            TransformProcessor("value", lambda v: v * 2, name="double_value")
        )
        metric_pipeline.add_processor(
            EnrichProcessor("processed", lambda r: True, name="mark_processed")
        )

        log_pipeline = Pipeline(name="logs", metrics_collector=mc, dead_letter_queue=dlq)
        log_pipeline.add_processor(
            TransformProcessor("source", str.upper, name="upper_source")
        )

        # Router
        router = Router(dead_letter_queue=dlq)
        router.add_route("metrics", metric_pipeline,
                         lambda r: r.get_field("type") == "metric", priority=5)
        router.add_route("logs", log_pipeline,
                         lambda r: r.get_field("type") == "log", priority=3)

        # Registry
        registry = PipelineRegistry()
        registry.register("metrics", metric_pipeline)
        registry.register("logs", log_pipeline)

        # Create and route records
        records = _make_records(10)
        routed = router.route_batch(records)

        all_results = []
        for pipeline_name, pipeline_records in routed.items():
            results = registry.execute(pipeline_name, pipeline_records)
            all_results.extend(results)

        assert len(all_results) == 10

        # Check metric records are doubled
        metric_results = [r for r in all_results if r.get_field("processed") is True]
        assert len(metric_results) == 5
        for r in metric_results:
            # Original values were 10,30,50,70,90 -> doubled to 20,60,100,140,180
            assert r.get_field("value") % 20 == 0

        # Reports
        rg = ReportGenerator(metrics_collector=mc, dead_letter_queue=dlq)
        report = rg.pipeline_report("metrics")
        assert report["total_records"] > 0

    def test_full_pipeline_with_aggregation(self):
        p = Pipeline(name="agg_test")
        p.add_processor(FilterProcessor(
            lambda r: r.get_field("value", 0) > 0, name="positive_filter"
        ))
        p.add_processor(AggregateProcessor("type", "value", agg_fn="sum", name="sum_agg"))
        records = _make_records(10)
        results = list(p.execute(records))
        assert len(results) == 2  # metric and log groups
        totals = {r.get_field("type"): r.get_field("value") for r in results}
        assert totals["metric"] == 10 + 30 + 50 + 70 + 90  # 250
        assert totals["log"] == 20 + 40 + 60 + 80 + 100  # 300


# --- Schema Evolution ---

class TestSchemaEvolution:
    def test_v1_records_through_v2_pipeline(self):
        sr = SchemaRegistry()
        v1 = _make_schema_v1()
        v2 = _make_schema_v2()
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)

        p = Pipeline(name="evolved", schema_registry=sr, target_schema=v2)
        p.add_processor(TransformProcessor("source", str.upper))
        p.add_processor(EnrichProcessor(
            "has_tags", lambda r: len(r.get_field("tags", [])) > 0
        ))

        # v1 records (no priority or tags fields)
        records = [
            Record(data={"type": "metric", "value": 42, "source": "sensor_a"}, schema=v1),
            Record(data={"type": "log", "value": 10}, schema=v1),
        ]
        results = list(p.execute(records))
        assert len(results) == 2
        # After migration, tags should default to []
        assert results[0].get_field("tags") == []
        assert results[0].get_field("priority") == 0
        assert results[0].get_field("source") == "SENSOR_A"
        assert results[0].get_field("has_tags") is False

    def test_migration_preserves_existing_data(self):
        sr = SchemaRegistry()
        v1 = _make_schema_v1()
        v2 = _make_schema_v2()
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)

        r = Record(data={"type": "metric", "value": 99, "source": "prod"}, schema=v1)
        migrated = migrator.migrate(r, v2)
        assert migrated.get_field("type") == "metric"
        assert migrated.get_field("value") == 99
        assert migrated.get_field("source") == "prod"

    def test_schema_registry_versioned_lookup(self):
        sr = SchemaRegistry()
        sr.register(_make_schema_v1())
        sr.register(_make_schema_v2())
        assert sr.get("event").version == 2
        assert sr.get("event", version=1).version == 1
        assert sr.get_versions("event") == [1, 2]


# --- DLQ + Retry Flow ---

class TestDLQRetryFlow:
    def test_dlq_retry_reprocessing(self):
        def fail_once(val):
            if val == "bad":
                raise ProcessorError("T", "r", "bad value")
            return val.upper()

        dlq = DeadLetterQueue()
        p = Pipeline(name="retry_test", dead_letter_queue=dlq)
        p.add_processor(TransformProcessor("x", fail_once, name="transformer"))

        records = [
            Record(data={"x": "good"}),
            Record(data={"x": "bad"}),
        ]
        results = list(p.execute(records))
        assert len(results) == 1
        assert dlq.count == 1

        # Retry: fix the data and reprocess
        entry = dlq.get_all()[0]
        failed_record = dlq.retry(entry.id)
        assert dlq.count == 0
        # Fix data
        fixed_record = failed_record.set_field("x", "fixed")
        p2 = Pipeline(name="retry_test")
        p2.add_processor(TransformProcessor("x", str.upper))
        retry_results = list(p2.execute([fixed_record]))
        assert retry_results[0].get_field("x") == "FIXED"

    def test_dlq_report_after_failures(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={}), "err1", processor_name="ProcA")
        dlq.add(Record(data={}), "err2", processor_name="ProcB")
        rg = ReportGenerator(dead_letter_queue=dlq)
        report = rg.dlq_report()
        assert report["total"] == 2
        assert "ProcA" in report["by_processor"]


# --- Lazy Streaming E2E ---

class TestLazyStreamingE2E:
    def test_lazy_end_to_end(self):
        def record_generator():
            for i in range(100):
                yield Record(data={"idx": i, "val": i * 10})

        p = Pipeline(name="lazy_test")
        p.add_processor(FilterProcessor(lambda r: r.get_field("val", 0) > 500))
        p.add_processor(TransformProcessor("val", lambda v: v + 1))

        gen = p.execute(record_generator())
        assert hasattr(gen, '__next__')

        results = list(gen)
        assert all(r.get_field("val") > 501 for r in results)
        assert len(results) == 49  # idx 51-99

    def test_lazy_with_aggregation(self):
        def record_generator():
            for i in range(20):
                yield Record(data={"cat": "A" if i < 10 else "B", "val": 1})

        p = Pipeline(name="lazy_agg")
        p.add_processor(AggregateProcessor("cat", "val", agg_fn="sum"))
        results = list(p.execute(record_generator()))
        totals = {r.get_field("cat"): r.get_field("val") for r in results}
        assert totals["A"] == 10
        assert totals["B"] == 10

    def test_execute_eager_materializes(self):
        p = Pipeline(name="eager_test")
        p.add_processor(TransformProcessor("x", str.upper))
        records = [Record(data={"x": "hello"})]
        results = p.execute_eager(records)
        assert isinstance(results, list)
        assert results[0].get_field("x") == "HELLO"


# --- Record Immutability Across Full Pipeline ---

class TestRecordImmutabilityE2E:
    def test_original_records_unchanged_after_pipeline(self):
        originals = [
            Record(data={"name": "alice", "score": 50}),
            Record(data={"name": "bob", "score": 75}),
        ]
        original_data = [r.to_dict() for r in originals]

        p = Pipeline(name="immutable_test")
        p.add_processor(TransformProcessor("name", str.upper))
        p.add_processor(EnrichProcessor("grade", lambda r: "A" if r.get_field("score", 0) > 60 else "B"))
        results = list(p.execute(originals))

        # Originals unchanged
        for i, r in enumerate(originals):
            assert r.to_dict()["data"] == original_data[i]["data"]

        # Results transformed
        assert results[0].get_field("name") == "ALICE"
        assert results[1].get_field("grade") == "A"

    def test_set_field_chain_immutability(self):
        r = Record(data={"a": 1, "b": 2})
        r2 = r.set_field("a", 10)
        r3 = r2.set_field("b", 20)
        assert r.get_field("a") == 1
        assert r.get_field("b") == 2
        assert r2.get_field("a") == 10
        assert r2.get_field("b") == 2
        assert r3.get_field("a") == 10
        assert r3.get_field("b") == 20


# --- Metrics Collection Across Pipeline ---

class TestMetricsAcrossPipeline:
    def test_metrics_across_multiple_pipelines(self):
        mc = MetricsCollector()
        p1 = Pipeline(name="pipeline_a", metrics_collector=mc)
        p1.add_processor(TransformProcessor("x", str.upper, name="upper"))
        p2 = Pipeline(name="pipeline_b", metrics_collector=mc)
        p2.add_processor(TransformProcessor("x", str.lower, name="lower"))

        list(p1.execute([Record(data={"x": "hello"})]))
        list(p2.execute([Record(data={"x": "WORLD"})]))

        all_metrics = mc.get_all_metrics()
        assert "upper" in all_metrics
        assert "lower" in all_metrics

        p1_metrics = mc.get_pipeline_metrics("pipeline_a")
        p2_metrics = mc.get_pipeline_metrics("pipeline_b")
        assert p1_metrics["total_records"] == 1
        assert p2_metrics["total_records"] == 1

    def test_metrics_with_failures(self):
        def sometimes_fail(val):
            if val == "bad":
                raise ProcessorError("T", "r", "fail")
            return val

        mc = MetricsCollector()
        dlq = DeadLetterQueue()
        p = Pipeline(name="fail_test", metrics_collector=mc, dead_letter_queue=dlq)
        p.add_processor(TransformProcessor("x", sometimes_fail, name="risky_proc"))

        records = [
            Record(data={"x": "good"}),
            Record(data={"x": "bad"}),
            Record(data={"x": "also_good"}),
        ]
        list(p.execute(records))

        metrics = mc.get_processor_metrics("risky_proc")
        assert metrics["success"] == 2
        assert metrics["failed"] == 1


# --- Case Insensitivity Throughout ---

class TestCaseInsensitivityE2E:
    def test_registry_case_insensitive(self):
        reg = PipelineRegistry()
        reg.register("MyPipeline", Pipeline())
        assert reg.get("mypipeline") is not None
        assert reg.get("MYPIPELINE") is not None

    def test_router_case_insensitive_remove(self):
        router = Router()
        router.add_route("MyRoute", Pipeline(), lambda r: True)
        router.remove_route("MYROUTE")
        assert len(router.get_routes()) == 0

    def test_pipeline_processor_case_insensitive_remove(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("x", str.upper, name="MyProc"))
        p.remove_processor("MYPROC")
        assert len(p.get_processors()) == 0

    def test_schema_registry_case_insensitive(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="UserEvent", version=1))
        result = sr.get("userevent")
        assert result is not None

    def test_dlq_get_by_processor_case_insensitive(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={}), "err", processor_name="MyProcessor")
        results = dlq.get_by_processor("myprocessor")
        assert len(results) == 1


# --- Defensive Copies Throughout ---

class TestDefensiveCopiesE2E:
    def test_record_to_dict_copy(self):
        r = Record(data={"items": [1, 2]}, metadata={"key": "val"})
        d = r.to_dict()
        d["data"]["items"].append(3)
        d["metadata"]["new_key"] = "new_val"
        assert r.data["items"] == [1, 2]
        assert "new_key" not in r.metadata

    def test_schema_to_dict_copy(self):
        s = Schema(name="test", fields={"x": {"type": "int", "required": True}})
        d = s.to_dict()
        d["fields"]["y"] = {"type": "str"}
        assert "y" not in s.fields

    def test_pipeline_get_processors_copy(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("x", str.upper, name="t1"))
        p.get_processors().clear()
        assert len(p.get_processors()) == 1

    def test_router_get_routes_copy(self):
        router = Router()
        router.add_route("r1", Pipeline(), lambda r: True)
        router.get_routes().clear()
        assert len(router.get_routes()) == 1

    def test_registry_list_pipelines_copy(self):
        reg = PipelineRegistry()
        reg.register("p1", Pipeline())
        reg.list_pipelines().clear()
        assert len(reg.list_pipelines()) == 1

    def test_dlq_get_all_copy(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={}), "err")
        dlq.get_all().clear()
        assert dlq.count == 1

    def test_execution_history_copy(self):
        p = Pipeline()
        list(p.execute([Record(data={"x": 1})]))
        p.get_execution_history().clear()
        assert len(p.get_execution_history()) == 1


# --- Serialization Round-Trip ---

class TestSerializationRoundTrip:
    def test_full_round_trip_with_schema(self):
        s = _make_schema_v1()
        r = Record(
            data={"type": "metric", "value": 42, "source": "test"},
            schema=s,
            metadata={"env": "prod"},
            source="api",
        )
        ser = RecordSerializer()
        d = ser.serialize(r)
        r2 = ser.deserialize(d)
        assert r2.id == r.id
        assert r2.data == r.data
        assert r2.metadata == r.metadata
        assert r2.source == r.source
        assert r2.schema.name == "event"

    def test_batch_round_trip(self):
        records = _make_records(5)
        ser = RecordSerializer()
        serialized = ser.serialize_batch(records)
        deserialized = ser.deserialize_batch(serialized)
        assert len(deserialized) == 5
        for orig, deser in zip(records, deserialized):
            assert orig.id == deser.id
            assert orig.data == deser.data

    def test_round_trip_preserves_status(self):
        r = Record(data={"x": 1})
        r.status = RecordStatus.PROCESSED
        ser = RecordSerializer()
        d = ser.serialize(r)
        r2 = ser.deserialize(d)
        assert r2.status == RecordStatus.PROCESSED

    def test_round_trip_with_errors(self):
        r = Record(data={"x": 1}, errors=["validation failed"])
        ser = RecordSerializer()
        d = ser.serialize(r)
        r2 = ser.deserialize(d)
        assert r2.errors == ["validation failed"]


# --- Backward Compatibility ---

class TestBackwardCompat:
    def test_pipeline_without_optional_params(self):
        p = Pipeline(name="basic")
        p.add_processor(TransformProcessor("x", str.upper))
        records = [Record(data={"x": "hello"})]
        results = list(p.execute(records))
        assert results[0].get_field("x") == "HELLO"

    def test_router_without_dlq(self):
        router = Router()
        router.add_route("default", Pipeline(), lambda r: True)
        r = Record(data={})
        assert router.route(r) == "default"

    def test_record_without_schema(self):
        r = Record(data={"anything": "goes"})
        assert r.is_valid() is True
        assert r.validate() == []

    def test_execute_eager_works_after_lazy_default(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("x", str.upper))
        results = p.execute_eager([Record(data={"x": "test"})])
        assert isinstance(results, list)
        assert results[0].get_field("x") == "TEST"
