from pathlib import Path

from fastapi.testclient import TestClient

from edgemock.gateway.app import build_gateway
from edgemock.config import ServiceConfig
from edgemock.gateway.validator import check_request, check_response

USERS_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Users", "version": "1"},
    "paths": {
        "/users": {
            "get": {
                "operationId": "list",
                "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer"}}],
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/User"}}}},
                    }
                },
            },
            "post": {
                "operationId": "create",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateUser"}}},
                },
                "responses": {
                    "201": {
                        "description": "created",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                    }
                },
            },
        },
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
                "required": ["id", "name", "email"],
            },
            "CreateUser": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "email": {"type": "string", "format": "email"}},
                "required": ["name", "email"],
            },
        }
    },
}


def test_request_no_violations():
    assert check_request("GET", "/users", {"limit": "10"}, None, USERS_SPEC) == []


def test_request_bad_query_type():
    v = check_request("GET", "/users", {"limit": "abc"}, None, USERS_SPEC)
    assert any("limit" in x for x in v)


def test_request_bad_body():
    v = check_request("POST", "/users", {}, {"name": 123}, USERS_SPEC)
    assert len(v) > 0


def test_response_no_violations():
    body = {"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Alice", "email": "a@b.com"}
    assert check_response("POST", "/users", 201, body, USERS_SPEC) == []


def test_response_missing_field():
    body = {"name": "Alice"}
    v = check_response("POST", "/users", 201, body, USERS_SPEC)
    assert len(v) > 0


def test_gateway_returns_502_on_unreachable(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title":"T","version":"1"}, "paths": {}}')
    svc = ServiceConfig(name="users", openapi=str(api), path="/users", port=9999)
    gw = build_gateway([svc], {"users": USERS_SPEC})
    client = TestClient(gw)
    assert client.get("/users").status_code == 502