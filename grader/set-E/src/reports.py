class ReportGenerator:
    def __init__(self, metrics_collector=None, dead_letter_queue=None):
        self.metrics_collector = metrics_collector
        self.dead_letter_queue = dead_letter_queue

    def pipeline_report(self, pipeline_name):
        if self.metrics_collector is None:
            return {
                "execution_count": 0,
                "total_records": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
            }
        m = self.metrics_collector.get_pipeline_metrics(pipeline_name)
        total = m.get("total_records", 0)
        success = m.get("success", 0)
        exec_count = m.get("execution_count", 0)
        duration = m.get("duration", 0.0)
        success_rate = (success / total * 100) if total > 0 else 0.0
        avg_duration = duration / exec_count if exec_count > 0 else 0.0
        return {
            "execution_count": exec_count,
            "total_records": total,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
        }

    def dlq_report(self):
        if self.dead_letter_queue is None:
            return {
                "total": 0,
                "by_processor": {},
                "oldest_entry": None,
                "newest_entry": None,
            }
        entries = self.dead_letter_queue.get_all()
        total = len(entries)
        by_processor = {}
        for entry in entries:
            pname = entry.processor_name or "unknown"
            by_processor[pname] = by_processor.get(pname, 0) + 1

        oldest = None
        newest = None
        if entries:
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)
            oldest = sorted_entries[0].to_dict()
            newest = sorted_entries[-1].to_dict()

        return {
            "total": total,
            "by_processor": by_processor,
            "oldest_entry": oldest,
            "newest_entry": newest,
        }

    def processor_performance_report(self):
        if self.metrics_collector is None:
            return {"processors": []}
        all_metrics = self.metrics_collector.get_all_metrics()
        processors = []
        for name, m in all_metrics.items():
            processors.append({
                "name": name,
                "total": m["total"],
                "success": m["success"],
                "failed": m["failed"],
                "avg_duration": m["avg_duration"],
            })
        processors.sort(key=lambda p: p["avg_duration"], reverse=True)
        return {"processors": processors}
