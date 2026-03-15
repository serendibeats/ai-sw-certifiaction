"""Step 8: Validation enhancement, reports, execution history, chain validation."""
import time
import pytest
from record import Record, RecordStatus, Schema
from validators import CompositeValidator, RequiredFieldValidator, TypeValidator
from processors import (
    TransformProcessor, FilterProcessor, EnrichProcessor, AggregateProcessor,
)
from pipeline import Pipeline
from metrics import MetricsCollector
from dead_letter import DeadLetterQueue
from reports import ReportGenerator


class TestCompositeValidatorStrict:
    def test_strict_mode_catches_unknown_fields(self):
        s = Schema(name="test", fields={"name": {"type": "str", "required": True}})
        r = Record(data={"name": "Alice", "extra": "field"}, schema=s)
        v = CompositeValidator([], strict=True)
        errors = v.validate(r)
        assert any("extra" in e for e in errors)

    def test_non_strict_allows_unknown_fields(self):
        s = Schema(name="test", fields={"name": {"type": "str", "required": True}})
        r = Record(data={"name": "Alice", "extra": "field"}, schema=s)
        v = CompositeValidator([], strict=False)
        errors = v.validate(r)
        assert len(errors) == 0

    def test_strict_with_validators(self):
        s = Schema(name="test", fields={
            "name": {"type": "str", "required": True},
            "age": {"type": "int", "required": True},
        })
        r = Record(data={"name": "Alice", "age": 30, "bonus": 100}, schema=s)
        v = CompositeValidator([
            RequiredFieldValidator(["name", "age"]),
        ], strict=True)
        errors = v.validate(r)
        assert any("bonus" in e for e in errors)


class TestPipelineValidation:
    def test_pipeline_validates_before_processing(self):
        dlq = DeadLetterQueue()
        v = RequiredFieldValidator(["name"])
        p = Pipeline(name="test", dead_letter_queue=dlq, validators=[v])
        p.add_processor(TransformProcessor("name", str.upper))
        records = [
            Record(data={"name": "Alice"}),
            Record(data={"age": 30}),  # missing name
        ]
        results = list(p.execute(records))
        assert len(results) == 1
        assert results[0].get_field("name") == "ALICE"
        assert dlq.count == 1

    def test_pipeline_validation_without_dlq(self):
        v = RequiredFieldValidator(["name"])
        p = Pipeline(name="test", validators=[v])
        records = [
            Record(data={"name": "Alice"}),
            Record(data={"age": 30}),  # missing name, dropped silently
        ]
        results = list(p.execute(records))
        assert len(results) == 1


class TestReportGenerator:
    def test_pipeline_report(self):
        mc = MetricsCollector()
        mc.record_pipeline_execution("p1", 100, 500.0, 95, 5)
        rg = ReportGenerator(metrics_collector=mc)
        report = rg.pipeline_report("p1")
        assert report["execution_count"] == 1
        assert report["total_records"] == 100
        assert report["success_rate"] == 95.0

    def test_pipeline_report_no_data(self):
        mc = MetricsCollector()
        rg = ReportGenerator(metrics_collector=mc)
        report = rg.pipeline_report("nonexistent")
        assert report["execution_count"] == 0
        assert report["success_rate"] == 0.0

    def test_pipeline_report_no_metrics(self):
        rg = ReportGenerator()
        report = rg.pipeline_report("any")
        assert report["execution_count"] == 0

    def test_dlq_report(self):
        dlq = DeadLetterQueue()
        dlq.add(Record(data={}), "err1", processor_name="ProcA")
        dlq.add(Record(data={}), "err2", processor_name="ProcB")
        dlq.add(Record(data={}), "err3", processor_name="ProcA")
        rg = ReportGenerator(dead_letter_queue=dlq)
        report = rg.dlq_report()
        assert report["total"] == 3
        assert report["by_processor"]["ProcA"] == 2
        assert report["by_processor"]["ProcB"] == 1
        assert report["oldest_entry"] is not None
        assert report["newest_entry"] is not None

    def test_dlq_report_empty(self):
        dlq = DeadLetterQueue()
        rg = ReportGenerator(dead_letter_queue=dlq)
        report = rg.dlq_report()
        assert report["total"] == 0
        assert report["oldest_entry"] is None

    def test_dlq_report_no_dlq(self):
        rg = ReportGenerator()
        report = rg.dlq_report()
        assert report["total"] == 0

    def test_processor_performance_report(self):
        mc = MetricsCollector()
        mc.record_processing("fast", 1.0, True)
        mc.record_processing("slow", 100.0, True)
        mc.record_processing("medium", 50.0, True)
        rg = ReportGenerator(metrics_collector=mc)
        report = rg.processor_performance_report()
        procs = report["processors"]
        assert len(procs) == 3
        assert procs[0]["name"] == "slow"  # sorted by avg_duration desc

    def test_processor_performance_report_empty(self):
        rg = ReportGenerator()
        report = rg.processor_performance_report()
        assert report["processors"] == []


class TestExecutionHistory:
    def test_execution_history_recorded(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("x", str.upper))
        list(p.execute([Record(data={"x": "a"})]))
        history = p.get_execution_history()
        assert len(history) == 1
        assert "record_count" in history[0]

    def test_get_last_execution(self):
        p = Pipeline(name="test")
        list(p.execute([Record(data={"x": "a"})]))
        list(p.execute([Record(data={"x": "b"}), Record(data={"x": "c"})]))
        last = p.get_last_execution()
        assert last is not None
        assert last["record_count"] == 2

    def test_get_last_execution_empty(self):
        p = Pipeline(name="test")
        assert p.get_last_execution() is None

    def test_execution_history_defensive_copy(self):
        p = Pipeline(name="test")
        list(p.execute([Record(data={"x": "a"})]))
        history = p.get_execution_history()
        history.clear()
        assert len(p.get_execution_history()) == 1


class TestChainValidation:
    def test_filter_before_aggregate_warning(self):
        p = Pipeline(name="test")
        p.add_processor(FilterProcessor(lambda r: True, name="filter1"))
        p.add_processor(AggregateProcessor("cat", "val", name="agg1"))
        warnings = p.validate_chain()
        assert len(warnings) >= 1
        assert any("filter1" in w and "agg1" in w for w in warnings)

    def test_no_warnings_for_safe_chain(self):
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("x", str.upper, name="transform"))
        p.add_processor(EnrichProcessor("y", lambda r: 1, name="enrich"))
        warnings = p.validate_chain()
        assert len(warnings) == 0

    def test_empty_chain_no_warnings(self):
        p = Pipeline(name="test")
        warnings = p.validate_chain()
        assert len(warnings) == 0
