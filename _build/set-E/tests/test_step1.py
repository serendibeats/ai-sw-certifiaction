"""Step 1: Record, Schema, Validators, Serializer foundation tests."""
import time
import pytest
from record import Record, RecordStatus, Schema
from validators import (
    Validator, RequiredFieldValidator, TypeValidator,
    RangeValidator, CompositeValidator,
)
from serializer import RecordSerializer
from errors import (
    RecordValidationError, SchemaError, ProcessorError,
    PipelineError, RouterError, SerializationError,
    InvalidRecordError, DuplicateRecordError,
)


class TestErrors:
    def test_pipeline_error(self):
        e = PipelineError("test error")
        assert "test error" in str(e)
        assert e.message == "test error"

    def test_record_validation_error(self):
        e = RecordValidationError(record_id="r1", errors=["bad field"])
        assert e.record_id == "r1"
        assert "bad field" in e.errors

    def test_processor_error(self):
        e = ProcessorError(processor_name="TestProc", record_id="r1")
        assert e.processor_name == "TestProc"
        assert e.record_id == "r1"

    def test_duplicate_record_error(self):
        e = DuplicateRecordError(record_id="r1")
        assert e.record_id == "r1"
        assert "r1" in str(e)

    def test_router_error(self):
        e = RouterError(record_id="r1")
        assert e.record_id == "r1"


class TestSchema:
    def test_schema_creation(self):
        s = Schema(name="test", version=1, fields={
            "name": {"type": "str", "required": True, "default": None},
            "age": {"type": "int", "required": False, "default": 0},
        })
        assert s.name == "test"
        assert s.version == 1
        assert len(s.fields) == 2

    def test_schema_validate_valid(self):
        s = Schema(name="test", fields={
            "name": {"type": "str", "required": True},
        })
        errors = s.validate({"name": "Alice"})
        assert len(errors) == 0

    def test_schema_validate_missing_required(self):
        s = Schema(name="test", fields={
            "name": {"type": "str", "required": True},
        })
        errors = s.validate({})
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_schema_validate_wrong_type(self):
        s = Schema(name="test", fields={
            "age": {"type": "int", "required": False},
        })
        errors = s.validate({"age": "not_a_number"})
        assert len(errors) == 1

    def test_schema_get_required_fields(self):
        s = Schema(name="test", fields={
            "name": {"type": "str", "required": True},
            "age": {"type": "int", "required": False},
            "email": {"type": "str", "required": True},
        })
        required = s.get_required_fields()
        assert "name" in required and "email" in required
        assert "age" not in required

    def test_schema_has_field(self):
        s = Schema(name="test", fields={"name": {"type": "str", "required": True}})
        assert s.has_field("name") is True
        assert s.has_field("nonexistent") is False

    def test_schema_to_dict(self):
        s = Schema(name="test", version=2, fields={"x": {"type": "int", "required": True}})
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["version"] == 2
        assert "x" in d["fields"]

    def test_schema_equality(self):
        s1 = Schema(name="test", version=1)
        s2 = Schema(name="test", version=1)
        s3 = Schema(name="test", version=2)
        assert s1 == s2
        assert s1 != s3


class TestRecord:
    def test_record_creation(self):
        r = Record(data={"name": "Alice"}, source="test")
        assert r.data["name"] == "Alice"
        assert r.status == RecordStatus.RAW
        assert r.source == "test"
        assert r.id is not None

    def test_record_get_field(self):
        r = Record(data={"name": "Alice", "age": 30})
        assert r.get_field("name") == "Alice"
        assert r.get_field("missing", "default") == "default"

    def test_record_set_field_returns_new(self):
        r = Record(data={"name": "Alice"})
        r2 = r.set_field("name", "Bob")
        assert r.get_field("name") == "Alice"  # original unchanged
        assert r2.get_field("name") == "Bob"

    def test_record_set_field_updates_timestamp(self):
        r = Record(data={"name": "Alice"})
        old_updated = r.updated_at
        time.sleep(0.01)
        r2 = r.set_field("name", "Bob")
        assert r2.updated_at >= old_updated

    def test_record_validate_with_schema(self):
        s = Schema(name="test", fields={
            "name": {"type": "str", "required": True},
        })
        r = Record(data={"name": "Alice"}, schema=s)
        assert r.is_valid() is True
        r2 = Record(data={}, schema=s)
        assert r2.is_valid() is False

    def test_record_validate_without_schema(self):
        r = Record(data={"anything": "goes"})
        assert r.validate() == []
        assert r.is_valid() is True

    def test_record_to_dict_deep_copy(self):
        r = Record(data={"items": [1, 2, 3]}, metadata={"tag": "test"})
        d = r.to_dict()
        d["data"]["items"].append(4)
        d["metadata"]["tag"] = "modified"
        assert r.data["items"] == [1, 2, 3]
        assert r.metadata["tag"] == "test"

    def test_record_copy(self):
        r = Record(data={"name": "Alice"}, metadata={"key": "val"})
        r2 = r.copy()
        assert r2.id == r.id
        assert r2.data == r.data
        r2.data["name"] = "Bob"
        assert r.data["name"] == "Alice"

    def test_record_status_enum(self):
        assert RecordStatus.RAW.value == "RAW"
        assert RecordStatus.PROCESSED.value == "PROCESSED"


class TestValidators:
    def test_required_field_validator_pass(self):
        r = Record(data={"name": "Alice", "age": 30})
        v = RequiredFieldValidator(["name", "age"])
        assert v.validate(r) == []

    def test_required_field_validator_fail(self):
        r = Record(data={"name": "Alice"})
        v = RequiredFieldValidator(["name", "age"])
        errors = v.validate(r)
        assert len(errors) == 1
        assert "age" in errors[0]

    def test_required_field_validator_none_value(self):
        r = Record(data={"name": None})
        v = RequiredFieldValidator(["name"])
        errors = v.validate(r)
        assert len(errors) == 1

    def test_type_validator_pass(self):
        r = Record(data={"age": 30})
        v = TypeValidator("age", int)
        assert v.validate(r) == []

    def test_type_validator_fail(self):
        r = Record(data={"age": "thirty"})
        v = TypeValidator("age", int)
        errors = v.validate(r)
        assert len(errors) == 1

    def test_type_validator_none_skips(self):
        r = Record(data={})
        v = TypeValidator("age", int)
        assert v.validate(r) == []

    def test_range_validator_pass(self):
        r = Record(data={"score": 75})
        v = RangeValidator("score", min_val=0, max_val=100)
        assert v.validate(r) == []

    def test_range_validator_below_min(self):
        r = Record(data={"score": -5})
        v = RangeValidator("score", min_val=0)
        errors = v.validate(r)
        assert len(errors) == 1

    def test_range_validator_above_max(self):
        r = Record(data={"score": 150})
        v = RangeValidator("score", max_val=100)
        errors = v.validate(r)
        assert len(errors) == 1

    def test_composite_validator(self):
        r = Record(data={"name": "Alice", "age": 30})
        v = CompositeValidator([
            RequiredFieldValidator(["name"]),
            TypeValidator("age", int),
        ])
        assert v.validate(r) == []

    def test_composite_validator_aggregates_errors(self):
        r = Record(data={})
        v = CompositeValidator([
            RequiredFieldValidator(["name"]),
            RequiredFieldValidator(["email"]),
        ])
        errors = v.validate(r)
        assert len(errors) == 2


class TestSerializer:
    def test_serialize_deserialize_round_trip(self):
        s = Schema(name="test", version=1, fields={"name": {"type": "str", "required": True}})
        r = Record(data={"name": "Alice"}, schema=s, source="input", metadata={"k": "v"})
        ser = RecordSerializer()
        d = ser.serialize(r)
        r2 = ser.deserialize(d)
        assert r2.id == r.id
        assert r2.data["name"] == "Alice"
        assert r2.source == "input"
        assert r2.metadata["k"] == "v"

    def test_serialize_batch(self):
        records = [Record(data={"i": i}) for i in range(3)]
        ser = RecordSerializer()
        batch = ser.serialize_batch(records)
        assert len(batch) == 3
        assert batch[1]["data"]["i"] == 1

    def test_deserialize_batch(self):
        data_list = [
            {"id": "r1", "data": {"name": "A"}, "status": "RAW"},
            {"id": "r2", "data": {"name": "B"}, "status": "PROCESSED"},
        ]
        ser = RecordSerializer()
        records = ser.deserialize_batch(data_list)
        assert len(records) == 2
        assert records[0].id == "r1"
        assert records[1].status == RecordStatus.PROCESSED

    def test_deserialize_with_schema_override(self):
        s = Schema(name="override", version=2)
        data = {"id": "r1", "data": {"x": 1}}
        ser = RecordSerializer()
        r = ser.deserialize(data, schema=s)
        assert r.schema.name == "override"
        assert r.schema.version == 2

    def test_deserialize_handles_missing_fields(self):
        data = {"data": {"x": 1}}
        ser = RecordSerializer()
        r = ser.deserialize(data)
        assert r.data["x"] == 1
        assert r.status == RecordStatus.RAW
        assert r.source == ""
