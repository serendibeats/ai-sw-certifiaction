from record import Record, RecordStatus


class Processor:
    @property
    def name(self):
        return self.__class__.__name__

    def process(self, record):
        return record


class FilterProcessor(Processor):
    def __init__(self, condition, name=None):
        self.condition = condition
        self._name = name

    @property
    def name(self):
        return self._name or "FilterProcessor"

    def process(self, record):
        if self.condition(record):
            return record
        return None


class TransformProcessor(Processor):
    def __init__(self, field, transform_fn, name=None):
        self.field = field
        self.transform_fn = transform_fn
        self._name = name

    @property
    def name(self):
        return self._name or "TransformProcessor"

    def process(self, record):
        value = record.get_field(self.field)
        if value is None:
            return record
        new_value = self.transform_fn(value)
        record = record.set_field(self.field, new_value)
        return record


class EnrichProcessor(Processor):
    def __init__(self, field, value_fn, name=None):
        self.field = field
        self.value_fn = value_fn
        self._name = name

    @property
    def name(self):
        return self._name or "EnrichProcessor"

    def process(self, record):
        value = self.value_fn(record)
        record = record.set_field(self.field, value)
        record.status = RecordStatus.ENRICHED
        return record


class AggregateProcessor(Processor):
    def __init__(self, group_by_field, agg_field, agg_fn="sum", name=None):
        self.group_by_field = group_by_field
        self.agg_field = agg_field
        self.agg_fn = agg_fn
        self._name = name
        self._groups = {}

    @property
    def name(self):
        return self._name or "AggregateProcessor"

    def process(self, record):
        group_key = record.get_field(self.group_by_field)
        if group_key not in self._groups:
            self._groups[group_key] = []
        self._groups[group_key].append(record.get_field(self.agg_field))
        return None

    def get_results(self):
        results = []
        for group_key, values in self._groups.items():
            if self.agg_fn == "sum":
                agg_value = sum(v for v in values if v is not None)
            elif self.agg_fn == "avg":
                valid = [v for v in values if v is not None]
                agg_value = sum(valid) / len(valid) if valid else 0
            elif self.agg_fn == "count":
                agg_value = len(values)
            elif self.agg_fn == "min":
                valid = [v for v in values if v is not None]
                agg_value = min(valid) if valid else None
            elif self.agg_fn == "max":
                valid = [v for v in values if v is not None]
                agg_value = max(valid) if valid else None
            else:
                agg_value = sum(v for v in values if v is not None)

            record = Record(data={
                self.group_by_field: group_key,
                self.agg_field: agg_value,
            })
            results.append(record)
        return results

    def reset(self):
        self._groups = {}
