from pathlib import Path

from fastapi.testclient import TestClient

from mockyard.mock.schema import generate
from mockyard.mock.generator import build
from mockyard.mock.store import Store


def test_fake_types():
    r = generate({"type": "string"})
    assert isinstance(r, str) and len(r) > 0

    r = generate({"type": "string", "format": "uuid"})
    assert isinstance(r, str) and len(r) == 36

    r = generate({"type": "string", "format": "email"})
    assert isinstance(r, str) and "@" in r, "email fail"

    r = generate({"type": "integer"})
    assert isinstance(r, int)

    r = generate({"type": "number"})
    assert isinstance(r, float)

    r = generate({"type": "array", "items": {"type": "string"}})
    assert isinstance(r, list) and len(r) == 1

    r = generate({"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}})
    assert isinstance(r, dict) and "name" in r and "age" in r


def test_fake_enum():
    r = generate({"type": "string", "enum": ["a", "b", "c"]})
    assert r == "a", str(r)


def test_fake_ref():
    components = {"schemas": {"X": {"type": "object", "properties": {"id": {"type": "string", "format": "uuid"}}}}}
    r = generate({"$ref": "#/components/schemas/X"}, components)
    assert isinstance(r, dict) and "id" in r


def test_deterministic():
    s = {"type": "object", "properties": {"name": {"type": "string"}}}
    assert generate(s, entity_id="x") == generate(s, entity_id="x")


def test_mock_app(tmp_path: Path):
    spec = tmp_path / "s.json"
    spec.write_text('{"openapi":"3.0.0","info":{"title":"T","version":"1"},"paths":'
                    '{"/items":{"get":{"operationId":"list","responses":{"200":{"description":"ok",'
                    '"content":{"application/json":{"schema":{"type":"array","items":{"type":"string"}}}}}}}}}}')
    app = build(spec)
    client = TestClient(app)
    assert client.get("/items").status_code == 200

    # post & get by id
    spec2 = tmp_path / "s2.json"
    spec2.write_text("""{"openapi":"3.0.0","info":{"title":"T","version":"1"},"paths":{"/items":{"post":{"operationId":"create","requestBody":{"required":true,"content":{"application/json":{"schema":{"type":"object","properties":{"name":{"type":"string"}}}}}},"responses":{"201":{"description":"ok","content":{"application/json":{"schema":{"type":"object"}}}}}},"/items/{id}":{"get":{"operationId":"get","parameters":[{"name":"id","in":"path","required":true,"schema":{"type":"string"}}],"responses":{"200":{"description":"ok","content":{"application/json":{"schema":{"type":"object"}}}}}}}}}}""")
    app2 = build(spec2)
    client2 = TestClient(app2)
    resp = client2.post("/items", json={"name": "hello"})
    assert resp.status_code == 201, resp.text


def test_store():
    s = Store()
    s.put("col", "1", {"val": 42})
    assert s.get("col", "1") == {"val": 42}
    assert len(s.list("col")) == 1
    assert s.delete("col", "1") is True
    assert s.get("col", "1") is None
