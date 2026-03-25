import time as _time
import uuid as _uuid
import copy as _copy
from processors import AggregateProcessor, FilterProcessor, TransformProcessor


class Pipeline:
    def __init__(self, name="default", schema_registry=None, target_schema=None,
                 metrics_collector=None, validators=None, dead_letter_queue=None):
        self.name = name
        self._processors = []
        self._execution_count = 0
        self.schema_registry = schema_registry
        self.target_schema = target_schema
        self.lazy = True
        self.dlq = dead_letter_queue
        self.metrics_collector = metrics_collector
        self.validators = validators or []
        self._executions = {}

    def set_dlq(self, dlq):
        self.dlq = dlq

    def add_processor(self, processor):
        self._processors.append(processor)
        return self

    def remove_processor(self, name):
        self._processors = [p for p in self._processors if p.name.lower() != name.lower()]

    def _migrate_records(self, records):
        if self.schema_registry is not None and self.target_schema is not None:
            from schema_registry import SchemaMigrator
            migrator = SchemaMigrator(self.schema_registry)
            for record in records:
                yield migrator.migrate(record, self.target_schema)
        else:
            yield from records

    def _validate_records(self, records):
        for record in records:
            errors = []
            for validator in self.validators:
                errors.extend(validator.validate(record))
            if errors:
                if self.dlq is not None:
                    self.dlq.add(record, str(errors), "validation")
                # Drop the record
            else:
                yield record

    def _build_gen(self, records):
        results = self._migrate_records(records)

        if self.validators:
            results = self._validate_records(results)

        for processor in self._processors:
            if isinstance(processor, AggregateProcessor):
                processor.reset()
                materialized = list(results)
                for record in materialized:
                    processor.process(record)
                results = iter(processor.get_results())
            else:
                results = self._apply_processor(processor, results)

        return results

    def _apply_processor(self, processor, records):
        for record in records:
            start = _time.time()
            try:
                result = processor.process(record)
                duration = (_time.time() - start) * 1000
                if self.metrics_collector is not None:
                    self.metrics_collector.record_processing(processor.name, duration, True)
                if result is not None:
                    yield result
            except Exception as e:
                duration = (_time.time() - start) * 1000
                if self.metrics_collector is not None:
                    self.metrics_collector.record_processing(processor.name, duration, False)
                if self.dlq is not None:
                    self.dlq.add(record, str(e), processor.name)
                else:
                    raise

    def _tracking_gen(self, records):
        """Wraps generator to track execution after consumption."""
        exec_id = str(_uuid.uuid4())
        start_time = _time.time()
        count = 0
        gen = self._build_gen(records)
        for item in gen:
            count += 1
            yield item
        # After generator is fully consumed
        duration = (_time.time() - start_time) * 1000
        exec_info = {
            "execution_id": exec_id,
            "timestamp": start_time,
            "record_count": count,
            "success_count": count,
            "fail_count": 0,
            "duration_ms": duration,
        }
        self._executions[exec_id] = exec_info
        if self.metrics_collector is not None:
            self.metrics_collector.record_pipeline_execution(
                self.name, count, duration, count, 0
            )

    def execute(self, records):
        self._execution_count += 1
        if self.lazy:
            return self._tracking_gen(records)
        return list(self._tracking_gen(records))

    def execute_eager(self, records):
        self._execution_count += 1
        return list(self._tracking_gen(records))

    def get_processors(self):
        return [p.name for p in self._processors]

    def get_execution_count(self):
        return self._execution_count

    def get_execution_history(self):
        return [_copy.deepcopy(v) for v in self._executions.values()]

    def get_last_execution(self):
        if not self._executions:
            return None
        last_key = list(self._executions.keys())[-1]
        return _copy.deepcopy(self._executions[last_key])

    def validate_chain(self):
        warnings = []
        for i, processor in enumerate(self._processors):
            if isinstance(processor, FilterProcessor):
                for j in range(i + 1, len(self._processors)):
                    if isinstance(self._processors[j], AggregateProcessor):
                        warnings.append(
                            f"FilterProcessor '{processor.name}' before AggregateProcessor '{self._processors[j].name}' may reduce aggregation input"
                        )
                        break
        return warnings
