"""Step 4: SchemaRegistry, SchemaMigrator, processor resilience with missing fields."""
import pytest
from record import Record, RecordStatus, Schema
from schema_registry import SchemaRegistry, SchemaMigrator
from processors import TransformProcessor, EnrichProcessor, FilterProcessor
from pipeline import Pipeline


class TestSchemaRegistry:
    def test_register_and_get(self):
        sr = SchemaRegistry()
        s = Schema(name="user", version=1, fields={"name": {"type": "str", "required": True}})
        sr.register(s)
        result = sr.get("user", version=1)
        assert result.name == "user"
        assert result.version == 1

    def test_get_latest_version(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="user", version=1))
        sr.register(Schema(name="user", version=2))
        sr.register(Schema(name="user", version=3))
        result = sr.get("user")
        assert result.version == 3

    def test_get_specific_version(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="user", version=1, fields={"a": {"type": "str"}}))
        sr.register(Schema(name="user", version=2, fields={"a": {"type": "str"}, "b": {"type": "int"}}))
        result = sr.get("user", version=1)
        assert len(result.fields) == 1

    def test_get_versions(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="user", version=1))
        sr.register(Schema(name="user", version=3))
        sr.register(Schema(name="user", version=2))
        versions = sr.get_versions("user")
        assert versions == [1, 2, 3]

    def test_get_versions_empty(self):
        sr = SchemaRegistry()
        assert sr.get_versions("nonexistent") == []

    def test_list_schemas(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="user", version=1))
        sr.register(Schema(name="order", version=1))
        names = sr.list_schemas()
        assert "user" in names
        assert "order" in names

    def test_get_not_found(self):
        sr = SchemaRegistry()
        with pytest.raises(KeyError):
            sr.get("nonexistent")

    def test_case_insensitive_lookup(self):
        sr = SchemaRegistry()
        sr.register(Schema(name="User", version=1))
        result = sr.get("user")
        assert result is not None


class TestSchemaMigrator:
    def test_migrate_adds_missing_fields(self):
        sr = SchemaRegistry()
        v1 = Schema(name="user", version=1, fields={
            "name": {"type": "str", "required": True, "default": None},
        })
        v2 = Schema(name="user", version=2, fields={
            "name": {"type": "str", "required": True, "default": None},
            "age": {"type": "int", "required": False, "default": 0},
            "email": {"type": "str", "required": False, "default": ""},
        })
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)
        r = Record(data={"name": "Alice"}, schema=v1)
        migrated = migrator.migrate(r, v2)
        assert migrated.get_field("name") == "Alice"
        assert migrated.get_field("age") == 0
        assert migrated.get_field("email") == ""
        assert migrated.schema == v2

    def test_migrate_keeps_extra_fields(self):
        sr = SchemaRegistry()
        v1 = Schema(name="user", version=1, fields={
            "name": {"type": "str", "required": True},
            "legacy_field": {"type": "str", "required": False},
        })
        v2 = Schema(name="user", version=2, fields={
            "name": {"type": "str", "required": True},
        })
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)
        r = Record(data={"name": "Alice", "legacy_field": "old"}, schema=v1)
        migrated = migrator.migrate(r, v2)
        assert migrated.get_field("legacy_field") == "old"

    def test_migrate_returns_new_record(self):
        sr = SchemaRegistry()
        v1 = Schema(name="user", version=1, fields={"name": {"type": "str", "required": True}})
        v2 = Schema(name="user", version=2, fields={
            "name": {"type": "str", "required": True},
            "age": {"type": "int", "required": False, "default": 0},
        })
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)
        r = Record(data={"name": "Alice"}, schema=v1)
        migrated = migrator.migrate(r, v2)
        assert r.schema == v1  # original unchanged
        assert "age" not in r.data

    def test_migrate_preserves_metadata(self):
        sr = SchemaRegistry()
        v1 = Schema(name="test", version=1, fields={})
        v2 = Schema(name="test", version=2, fields={"x": {"type": "int", "default": 0}})
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)
        r = Record(data={}, schema=v1, metadata={"source": "test"})
        migrated = migrator.migrate(r, v2)
        assert migrated.metadata["source"] == "test"


class TestProcessorResilienceWithMissingFields:
    def test_transform_missing_field_skips(self):
        tp = TransformProcessor("nonexistent", str.upper)
        r = Record(data={"other": "value"})
        result = tp.process(r)
        assert result is not None
        assert result.get_field("other") == "value"

    def test_enrich_with_missing_source(self):
        ep = EnrichProcessor(
            "full_name",
            lambda rec: f"{rec.get_field('first', 'Unknown')} {rec.get_field('last', 'Unknown')}",
        )
        r = Record(data={})
        result = ep.process(r)
        assert result.get_field("full_name") == "Unknown Unknown"

    def test_filter_missing_field_no_match(self):
        fp = FilterProcessor(lambda r: r.get_field("status") == "active")
        r = Record(data={})
        result = fp.process(r)
        assert result is None

    def test_pipeline_with_schema_migration(self):
        sr = SchemaRegistry()
        v1 = Schema(name="data", version=1, fields={
            "value": {"type": "int", "required": True},
        })
        v2 = Schema(name="data", version=2, fields={
            "value": {"type": "int", "required": True},
            "label": {"type": "str", "required": False, "default": "none"},
        })
        sr.register(v1)
        sr.register(v2)
        migrator = SchemaMigrator(sr)

        p = Pipeline(name="test", schema_registry=sr, target_schema=v2)
        p.add_processor(TransformProcessor("label", str.upper))

        r = Record(data={"value": 42}, schema=v1)
        results = list(p.execute([r]))
        assert len(results) == 1
        assert results[0].get_field("label") == "NONE"
