import copy


class MetricsCollector:
    def __init__(self):
        self._processor_metrics = {}
        self._pipeline_metrics = {}

    def record_processing(self, processor_name, duration_ms, success):
        if processor_name not in self._processor_metrics:
            self._processor_metrics[processor_name] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "total_duration": 0.0,
            }
        m = self._processor_metrics[processor_name]
        m["total"] += 1
        if success:
            m["success"] += 1
        else:
            m["failed"] += 1
        m["total_duration"] += duration_ms

    def get_processor_metrics(self, processor_name):
        if processor_name not in self._processor_metrics:
            return {"total": 0, "success": 0, "failed": 0, "avg_duration": 0.0}
        m = self._processor_metrics[processor_name]
        avg = m["total_duration"] / m["total"] if m["total"] > 0 else 0.0
        return {
            "total": m["total"],
            "success": m["success"],
            "failed": m["failed"],
            "avg_duration": avg,
        }

    def get_all_metrics(self):
        result = {}
        for name in self._processor_metrics:
            result[name] = self.get_processor_metrics(name)
        return result

    def record_pipeline_execution(self, pipeline_name, record_count, duration_ms, success_count, fail_count):
        if pipeline_name not in self._pipeline_metrics:
            self._pipeline_metrics[pipeline_name] = {
                "total_records": 0,
                "success": 0,
                "failed": 0,
                "duration": 0.0,
                "execution_count": 0,
            }
        m = self._pipeline_metrics[pipeline_name]
        m["total_records"] += record_count
        m["success"] += success_count
        m["failed"] += fail_count
        m["duration"] += duration_ms
        m["execution_count"] += 1

    def get_pipeline_metrics(self, pipeline_name):
        if pipeline_name not in self._pipeline_metrics:
            return {
                "total_records": 0,
                "success": 0,
                "failed": 0,
                "duration": 0.0,
                "execution_count": 0,
            }
        return copy.deepcopy(self._pipeline_metrics[pipeline_name])

    def reset(self):
        self._processor_metrics.clear()
        self._pipeline_metrics.clear()
