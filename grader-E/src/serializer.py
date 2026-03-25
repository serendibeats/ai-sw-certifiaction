from record import Record, RecordStatus, Schema


class RecordSerializer:
    def serialize(self, record):
        return record.to_dict()

    def deserialize(self, data, schema=None):
        status = data.get("status", "RAW")
        if isinstance(status, str):
            status = RecordStatus(status)

        if schema is None and "schema" in data and data["schema"] is not None:
            schema_data = data["schema"]
            schema = Schema(
                name=schema_data.get("name"),
                version=schema_data.get("version", 1),
                fields=schema_data.get("fields", {}),
            )

        return Record(
            record_id=data.get("id"),
            data=data.get("data", {}),
            schema=schema,
            status=status,
            metadata=data.get("metadata", {}),
            source=data.get("source", ""),
            errors=data.get("errors", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def serialize_batch(self, records):
        return [self.serialize(r) for r in records]

    def deserialize_batch(self, data_list, schema=None):
        return [self.deserialize(d, schema=schema) for d in data_list]
