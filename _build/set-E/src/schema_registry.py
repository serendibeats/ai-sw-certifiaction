import copy
from record import Record


class SchemaRegistry:
    def __init__(self):
        self._schemas = {}  # name_lower -> {version: schema}

    def register(self, schema):
        key = schema.name.lower()
        if key not in self._schemas:
            self._schemas[key] = {}
        self._schemas[key][schema.version] = schema

    def get(self, name, version=None):
        key = name.lower()
        if key not in self._schemas:
            raise KeyError(f"Schema '{name}' not found")
        versions = self._schemas[key]
        if version is not None:
            if version not in versions:
                raise KeyError(f"Schema '{name}' version {version} not found")
            return versions[version]
        # Return latest version
        latest = max(versions.keys())
        return versions[latest]

    def get_versions(self, name):
        key = name.lower()
        if key not in self._schemas:
            return []
        return sorted(self._schemas[key].keys())

    def list_schemas(self):
        result = []
        seen = set()
        for key, versions in self._schemas.items():
            # Use the name from one of the schema objects
            for v, schema in versions.items():
                if key not in seen:
                    result.append(schema.name)
                    seen.add(key)
                break
        return result


class SchemaMigrator:
    def __init__(self, schema_registry):
        self.schema_registry = schema_registry

    def migrate(self, record, target_schema):
        new_data = copy.deepcopy(record.data)

        # Add missing fields with defaults from target schema
        for field_name, field_def in target_schema.fields.items():
            if field_name not in new_data:
                if "default" in field_def:
                    new_data[field_name] = field_def["default"]

        new_record = Record(
            record_id=record.id,
            data=new_data,
            schema=target_schema,
            status=record.status,
            metadata=copy.deepcopy(record.metadata),
            source=record.source,
            errors=list(record.errors),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        return new_record
