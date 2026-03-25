class PipelineError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class RecordValidationError(PipelineError):
    def __init__(self, record_id, errors):
        self.record_id = record_id
        self.errors = errors
        message = f"Validation failed for record {record_id}: {errors}"
        super().__init__(message)


class SchemaError(PipelineError):
    def __init__(self, message):
        super().__init__(message)


class ProcessorError(PipelineError):
    def __init__(self, processor_name=None, record_id=None, message=None):
        self.processor_name = processor_name
        self.record_id = record_id
        msg = message or f"Processor error in {processor_name} for record {record_id}"
        super().__init__(msg)


class RouterError(PipelineError):
    def __init__(self, record_id=None, message=None):
        self.record_id = record_id
        msg = message or f"Routing error for record {record_id}"
        super().__init__(msg)


class SerializationError(PipelineError):
    def __init__(self, message):
        super().__init__(message)


class InvalidRecordError(PipelineError):
    def __init__(self, message):
        super().__init__(message)


class DuplicateRecordError(PipelineError):
    def __init__(self, record_id):
        self.record_id = record_id
        message = f"Duplicate record: {record_id}"
        super().__init__(message)
