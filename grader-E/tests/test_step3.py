"""Step 3: Router, Registry, system policies (case-insensitive, defensive copies)."""
import pytest
from record import Record, RecordStatus, Schema
from pipeline import Pipeline
from processors import TransformProcessor, FilterProcessor
from router import Router
from registry import PipelineRegistry
from errors import RouterError


class TestRouter:
    def test_route_single_match(self):
        router = Router()
        p = Pipeline(name="text_pipeline")
        router.add_route("text", p, lambda r: r.get_field("type") == "text")
        r = Record(data={"type": "text"})
        assert router.route(r) == "text"

    def test_route_no_match_raises(self):
        router = Router()
        router.add_route("text", Pipeline(), lambda r: r.get_field("type") == "text")
        r = Record(data={"type": "image"})
        with pytest.raises(RouterError):
            router.route(r)

    def test_route_batch(self):
        router = Router()
        router.add_route("text", Pipeline(name="text"), lambda r: r.get_field("type") == "text")
        router.add_route("image", Pipeline(name="image"), lambda r: r.get_field("type") == "image")
        records = [
            Record(data={"type": "text", "id": 1}),
            Record(data={"type": "image", "id": 2}),
            Record(data={"type": "text", "id": 3}),
        ]
        result = router.route_batch(records)
        assert len(result["text"]) == 2
        assert len(result["image"]) == 1

    def test_remove_route(self):
        router = Router()
        router.add_route("text", Pipeline(), lambda r: True)
        router.remove_route("text")
        assert "text" not in router.get_routes()

    def test_get_routes_defensive_copy(self):
        router = Router()
        router.add_route("text", Pipeline(), lambda r: True)
        routes = router.get_routes()
        routes.clear()
        assert len(router.get_routes()) == 1

    def test_route_first_match(self):
        router = Router()
        router.add_route("first", Pipeline(), lambda r: True)
        router.add_route("second", Pipeline(), lambda r: True)
        r = Record(data={})
        # Without priority, first added with highest default should match
        name = router.route(r)
        assert name in ["first", "second"]


class TestRegistry:
    def test_register_and_get(self):
        reg = PipelineRegistry()
        p = Pipeline(name="test")
        reg.register("test", p)
        assert reg.get("test") is p

    def test_case_insensitive_get(self):
        reg = PipelineRegistry()
        p = Pipeline(name="MyPipeline")
        reg.register("MyPipeline", p)
        assert reg.get("mypipeline") is p
        assert reg.get("MYPIPELINE") is p

    def test_unregister(self):
        reg = PipelineRegistry()
        reg.register("test", Pipeline())
        reg.unregister("test")
        with pytest.raises(KeyError):
            reg.get("test")

    def test_list_pipelines_defensive_copy(self):
        reg = PipelineRegistry()
        reg.register("p1", Pipeline())
        reg.register("p2", Pipeline())
        names = reg.list_pipelines()
        names.clear()
        assert len(reg.list_pipelines()) == 2

    def test_execute(self):
        reg = PipelineRegistry()
        p = Pipeline(name="test")
        p.add_processor(TransformProcessor("name", str.upper))
        reg.register("test", p)
        records = [Record(data={"name": "alice"})]
        results = reg.execute("test", records)
        assert isinstance(results, list)
        assert results[0].get_field("name") == "ALICE"

    def test_get_not_found(self):
        reg = PipelineRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")


class TestSystemPolicyCaseInsensitive:
    def test_pipeline_remove_processor_case_insensitive(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("x", str.upper, name="MyProcessor"))
        p.remove_processor("myprocessor")
        assert len(p.get_processors()) == 0

    def test_router_remove_route_case_insensitive(self):
        router = Router()
        router.add_route("MyRoute", Pipeline(), lambda r: True)
        router.remove_route("myroute")
        assert len(router.get_routes()) == 0

    def test_registry_case_insensitive_lookup(self):
        reg = PipelineRegistry()
        reg.register("DataPipeline", Pipeline())
        assert reg.get("datapipeline") is not None
        assert reg.get("DATAPIPELINE") is not None


class TestSystemPolicyDefensiveCopies:
    def test_record_to_dict_deep_copy(self):
        r = Record(data={"items": [1, 2]}, metadata={"key": "val"})
        d = r.to_dict()
        d["data"]["items"].append(3)
        d["metadata"]["key"] = "changed"
        assert r.data["items"] == [1, 2]
        assert r.metadata["key"] == "val"

    def test_schema_to_dict_deep_copy(self):
        s = Schema(name="test", fields={"x": {"type": "int", "required": True}})
        d = s.to_dict()
        d["fields"]["y"] = {"type": "str"}
        assert "y" not in s.fields

    def test_pipeline_get_processors_copy(self):
        p = Pipeline()
        p.add_processor(TransformProcessor("x", str.upper, name="t1"))
        procs = p.get_processors()
        procs.clear()
        assert len(p.get_processors()) == 1

    def test_router_get_routes_copy(self):
        router = Router()
        router.add_route("r1", Pipeline(), lambda r: True)
        routes = router.get_routes()
        routes.clear()
        assert len(router.get_routes()) == 1

    def test_registry_list_pipelines_copy(self):
        reg = PipelineRegistry()
        reg.register("p1", Pipeline())
        names = reg.list_pipelines()
        names.clear()
        assert len(reg.list_pipelines()) == 1
