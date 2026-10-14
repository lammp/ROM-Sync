"""Declared models and one error envelope (F10-S1)."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel

from romsync.domain.errors import GuardRefused, UnknownDevice
from romsync_api.app import PREFIX, ROUTERS, create_app
from romsync_api.models import Model
from tests.unit.api.conftest import BASE


def api_routes() -> list[APIRoute]:
    return [r for router in ROUTERS for r in router.routes if isinstance(r, APIRoute)]


def test_models_declared(app: FastAPI) -> None:
    routes = api_routes()
    assert routes
    for route in routes:
        model = route.response_model
        # A binary answer (a cover) cannot be a model; it declares its media types instead.
        binary = set(route.responses.get(200, {}).get("content", {})) - {"application/json"}
        assert (isinstance(model, type) and issubclass(model, Model)) or (
            model is None and binary
        ), f"{route.path} returns no declared model and declares no media type"
    document = app.openapi()
    assert document["paths"]
    for path, operations in document["paths"].items():
        assert path.startswith(PREFIX), path
        for method, operation in operations.items():
            for status in ("400", "404", "422"):
                schema = operation["responses"][status]["content"]["application/json"]["schema"]
                assert schema == {"$ref": "#/components/schemas/ErrorEnvelope"}, (
                    f"{method} {path} declares no error shape for {status}"
                )


def test_a_model_refuses_what_it_does_not_declare() -> None:
    class Probe(Model):
        a: int

    assert issubclass(Probe, BaseModel)
    try:
        Probe(a=1, b=2)  # type: ignore[call-arg]
    except ValueError:
        return
    raise AssertionError("an undeclared field was accepted")


class Body(Model):
    count: int


def _with_failures() -> TestClient:
    app = create_app(None)
    router = APIRouter()

    @router.get("/boom/guard", response_model=Body)
    def guard() -> Body:
        raise GuardRefused("saves are never removed", field="name")

    @router.get("/boom/device", response_model=Body)
    def device() -> Body:
        raise UnknownDevice("that device is not attached", field="device")

    @router.post("/boom/body", response_model=Body)
    def body(payload: Body) -> Body:
        return payload

    app.include_router(router, prefix=PREFIX)
    return TestClient(app, base_url=BASE)


def test_error_envelope() -> None:
    client = _with_failures()
    refused = client.get(f"{PREFIX}/boom/guard")
    assert refused.status_code == 409
    assert refused.json() == {
        "error": {
            "code": "guard.refused",
            "message": "saves are never removed",
            "field": "name",
        }
    }
    assert client.get(f"{PREFIX}/boom/device").status_code == 404
    token = client.get(f"{PREFIX}/session").json()["token"]
    invalid = client.post(
        f"{PREFIX}/boom/body",
        json={"count": "many"},
        headers={"Origin": BASE, "X-RomSync-Token": token},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "request.invalid"
    assert invalid.json()["error"]["field"] == "count"
    missing = client.get(f"{PREFIX}/no-such-route")
    assert missing.status_code == 404
    assert set(missing.json()) == {"error"}
    assert missing.json()["error"]["code"] == "request.not_found"
    wrong_method = client.delete(
        f"{PREFIX}/version", headers={"Origin": BASE, "X-RomSync-Token": token}
    )
    assert wrong_method.json()["error"]["code"] == "request.method"


def test_version(client: TestClient) -> None:
    got = client.get(f"{PREFIX}/version")
    assert got.status_code == 200
    assert got.json() == {"application": "ROM-Sync", "version": "2.0.0", "api": "v1"}


def test_an_app_built_to_describe_itself_has_no_engine() -> None:
    from fastapi import Depends

    from romsync.compose import Engine
    from romsync_api.deps import engine as engine_of

    app = create_app(None)
    router = APIRouter()

    @router.get("/needs-engine", response_model=Body)
    def needs(engine: Engine = Depends(engine_of)) -> Body:  # noqa: B008
        return Body(count=1)

    app.include_router(router, prefix=PREFIX)
    got = TestClient(app, base_url=BASE).get(f"{PREFIX}/needs-engine")
    assert got.json()["error"]["code"] == "request.no_engine"
