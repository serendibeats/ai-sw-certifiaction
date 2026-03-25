import uuid
import time
import copy
from enum import Enum


class RecordStatus(Enum):
    RAW = "RAW"
    VALIDATED = "VALIDATED"
    PROCESSED = "PROCESSED"
    ENRICHED = "ENRICHED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class Schema:
    def __init__(self, name, version=1, fields=None):
        self.name = name
        self.version = version
        self.fields = fields if fields is not None else {}

    def validate(self, data):
        errors = []
        for field_name, field_def in self.fields.items():
            if field_def.get("required", False):
                if field_name not in data or data[field_name] is None:
                    errors.append(f"Missing required field: {field_name}")
                    continue
            if field_name in data and data[field_name] is not None:
                expected_type = field_def.get("type")
                if expected_type:
                    type_map = {
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "list": list,
                        "dict": dict,
                        "string": str,
                        "integer": int,
                        "number": (int, float),
                    }
                    expected = type_map.get(expected_type, str)
                    if not isinstance(data[field_name], expected if isinstance(expected, tuple) else expected):
                        errors.append(f"Field {field_name} expected type {expected_type}, got {type(data[field_name]).__name__}")
        return errors

    def get_required_fields(self):
        return [name for name, field_def in self.fields.items() if field_def.get("required", False)]

    def has_field(self, name):
        return name in self.fields

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "fields": copy.deepcopy(self.fields),
        }

    def __eq__(self, other):
        if not isinstance(other, Schema):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __hash__(self):
        return hash((self.name, self.version))


class Record:
    def __init__(self, data=None, schema=None, record_id=None, status=RecordStatus.RAW,
                 metadata=None, source="", errors=None, created_at=None, updated_at=None):
        self.id = record_id if record_id is not None else str(uuid.uuid4())
        self.data = data if data is not None else {}
        self.schema = schema
        self.status = status
        self.metadata = metadata if metadata is not None else {}
        self.source = source
        self.errors = errors if errors is not None else []
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else time.time()

    def get_field(self, name, default=None):
        return self.data.get(name, default)

    def set_field(self, name, value):
        new_data = copy.deepcopy(self.data)
        new_data[name] = value
        new_record = Record(
            record_id=self.id,
            data=new_data,
            schema=self.schema,
            status=self.status,
            metadata=copy.deepcopy(self.metadata),
            source=self.source,
            errors=list(self.errors),
            created_at=self.created_at,
            updated_at=time.time(),
        )
        return new_record

    def copy(self):
        return Record(
            record_id=self.id,
            data=copy.deepcopy(self.data),
            schema=self.schema,
            status=self.status,
            metadata=copy.deepcopy(self.metadata),
            source=self.source,
            errors=list(self.errors),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def validate(self):
        if self.schema is None:
            return []
        return self.schema.validate(self.data)

    def is_valid(self):
        return len(self.validate()) == 0

    def to_dict(self):
        result = {
            "id": self.id,
            "data": copy.deepcopy(self.data),
            "status": self.status.value if isinstance(self.status, RecordStatus) else self.status,
            "metadata": copy.deepcopy(self.metadata),
            "source": self.source,
            "errors": list(self.errors),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.schema is not None:
            result["schema"] = self.schema.to_dict()
        return result
