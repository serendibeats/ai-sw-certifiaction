class Validator:
    @property
    def name(self):
        return self.__class__.__name__

    def validate(self, record):
        return []


class RequiredFieldValidator(Validator):
    def __init__(self, fields):
        self.fields = fields

    def validate(self, record):
        errors = []
        for field in self.fields:
            value = record.get_field(field)
            if value is None:
                errors.append(f"Missing required field: {field}")
        return errors


class TypeValidator(Validator):
    def __init__(self, field, expected_type):
        self.field = field
        self.expected_type = expected_type

    def validate(self, record):
        errors = []
        value = record.get_field(self.field)
        if value is not None and not isinstance(value, self.expected_type):
            errors.append(
                f"Field {self.field} expected type {self.expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        return errors


class RangeValidator(Validator):
    def __init__(self, field, min_val=None, max_val=None):
        self.field = field
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, record):
        errors = []
        value = record.get_field(self.field)
        if value is not None:
            if self.min_val is not None and value < self.min_val:
                errors.append(f"Field {self.field} value {value} is below minimum {self.min_val}")
            if self.max_val is not None and value > self.max_val:
                errors.append(f"Field {self.field} value {value} is above maximum {self.max_val}")
        return errors


class CompositeValidator(Validator):
    def __init__(self, validators, strict=False):
        self.validators = validators
        self.strict = strict

    def validate(self, record):
        errors = []
        for validator in self.validators:
            errors.extend(validator.validate(record))
        if self.strict and record.schema is not None:
            schema_fields = set(record.schema.fields.keys())
            data_fields = set(record.data.keys())
            extra = data_fields - schema_fields
            for field in sorted(extra):
                errors.append(f"Unknown field: {field}")
        return errors
