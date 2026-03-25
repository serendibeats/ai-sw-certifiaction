class PipelineRegistry:
    def __init__(self):
        self._pipelines = {}

    def register(self, name, pipeline):
        self._pipelines[name.lower()] = (name, pipeline)

    def unregister(self, name):
        key = name.lower()
        if key in self._pipelines:
            del self._pipelines[key]

    def get(self, name):
        key = name.lower()
        if key not in self._pipelines:
            raise KeyError(f"Pipeline '{name}' not found")
        return self._pipelines[key][1]

    def list_pipelines(self):
        return [orig_name for orig_name, pipeline in self._pipelines.values()]

    def execute(self, name, records):
        pipeline = self.get(name)
        result = pipeline.execute(records)
        if not isinstance(result, list):
            result = list(result)
        return result
