import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from mockyard.mock.schema import generate
from mockyard.mock.store import Store

# global in-memory store for mock data
_store = Store()


def _load(path: Path) -> dict:
    """load & validate openapi spec. returns parsed dict."""
    spec = json.loads(path.read_text())
    if not isinstance(spec, dict) or "paths" not in spec:
        raise ValueError(f"invalid openapi: no paths in {path}")
    return spec


def _convert_path(url: str) -> str:
    """/users/{id} -> /users/{id} (fastapi-compatible path)."""
    return re.sub(r"\{(\w+)\}", r"{\1}", url)


def _collection_from(path: str) -> str:
    """extract collection name from first non-param path segment."""
    parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]
    return parts[0] if parts else "default"


def _make_handler(method: str, path: str, op: dict, components: dict):
    """factory: returns an async handler for a given endpoint definition."""
    col = _collection_from(path)

    # grab response schema
    responses = op.get("responses", {})
    ok_resp = responses.get("200") or responses.get("201") or responses.get("default")
    resp_schema = None
    if ok_resp:
        content = ok_resp.get("content", {})
        json_content = content.get("application/json", {})
        resp_schema = json_content.get("schema")

    # grab request body schema
    body_schema = None
    if "requestBody" in op:
        rb = op["requestBody"]
        rb_content = rb.get("content", {})
        rb_json = rb_content.get("application/json", {})
        body_schema = rb_json.get("schema")

    async def handler(request: Request) -> Response:
        path_id = None
        if m := re.search(r"/([^/]+)$", path):
            candidate = request.path_params.get(m.group(1).strip("{}"))
            if candidate:
                path_id = str(candidate)

        method_upper = method.upper()
        if method_upper == "GET":
            if path_id:
                item = _store.get(col, path_id)
                if item is not None:
                    return JSONResponse(item)
            else:
                items = _store.list(col)
                if items:
                    return JSONResponse(items)
            if resp_schema:
                return JSONResponse(generate(resp_schema, components, f"{col}.{path_id or 'list'}"))
            return JSONResponse([])

        elif method_upper == "POST":
            body = await request.json()
            new_id = uuid.uuid4().hex[:12]
            _store.put(col, new_id, body)
            return JSONResponse(body, status_code=201)

        elif method_upper == "PUT":
            body = await request.json()
            if path_id:
                _store.put(col, path_id, body)
            return JSONResponse(body)

        elif method_upper == "DELETE":
            if path_id:
                _store.delete(col, path_id)
            return Response(status_code=204)

        else:
            return JSONResponse({"error": "unsupported"}, status_code=405)

    return handler


def build(openapi_path: Path) -> FastAPI:
    """build a mock FastAPI app from an openapi spec file."""
    spec = _load(openapi_path)
    components = spec.get("components", {})
    info = spec.get("info", {})
    title = info.get("title", "Mock")
    version = info.get("version", "0.0.0")

    app = FastAPI(title=f"{title} (Mock)", version=version)
    router = APIRouter()

    for url, methods in spec.get("paths", {}).items():
        fastapi_url = _convert_path(url)
        for method, op in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE"):
                continue
            handler = _make_handler(method, url, op, components)
            handler.__name__ = op.get("operationId", f"{method}_{url.replace('/', '_')}")
            router.add_api_route(fastapi_url, handler, methods=[method.upper()], include_in_schema=False)

    app.include_router(router)
    return app
