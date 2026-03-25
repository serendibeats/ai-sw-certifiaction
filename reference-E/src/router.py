from errors import RouterError


class Router:
    def __init__(self, dead_letter_queue=None):
        self._routes = []
        self._dlq = dead_letter_queue

    def add_route(self, name, pipeline, condition, priority=0):
        self._routes.append({
            "name": name,
            "pipeline": pipeline,
            "condition": condition,
            "priority": priority,
        })

    def remove_route(self, name):
        self._routes = [r for r in self._routes if r["name"].lower() != name.lower()]

    def _sorted_routes(self):
        return sorted(self._routes, key=lambda r: r["priority"], reverse=True)

    def route(self, record):
        for r in self._sorted_routes():
            if r["condition"](record):
                return r["name"]
        if self._dlq is not None:
            self._dlq.add(record)
            return None
        raise RouterError(record_id=getattr(record, 'id', None), message=f"No matching route for record")

    def route_batch(self, records):
        result = {}
        for record in records:
            route_name = self.route(record)
            if route_name is not None:
                if route_name not in result:
                    result[route_name] = []
                result[route_name].append(record)
        return result

    def get_routes(self):
        return [r["name"] for r in self._routes]

    def set_dlq(self, dlq):
        self._dlq = dlq
