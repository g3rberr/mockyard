import json
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx

from edgemock.config import ServiceConfig
from edgemock.gateway.validator import check_request, check_response
from edgemock.gateway.recorder import Recorder
from edgemock.ui.console import console, print_violation


def build_gateway(services: list[ServiceConfig], specs: dict[str, dict], recorder: Recorder | None = None) -> FastAPI:
    app = FastAPI(title="edge-mock gateway", version="0.1.0")
    client = httpx.AsyncClient()

    by_prefix = {}
    for svc in services:
        by_prefix[svc.path.rstrip("/")] = svc

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy(request: Request, path: str):
        full = f"/{path}"
        method = request.method

        svc = _pick_service(full, by_prefix)
        if not svc:
            return JSONResponse({"error": "no matching service"}, status_code=502)

        target = f"http://127.0.0.1:{svc.port}{full}"
        body_bytes = await request.body()
        body = None
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = body_bytes.decode()

        spec = specs.get(svc.name)
        if spec:
            for v in check_request(method, full, dict(request.query_params), body, spec):
                print_violation(svc.name, method, full, v)

        headers = dict(request.headers)
        headers.pop("host", None)
        try:
            resp = await client.request(method, target, headers=headers, content=body_bytes,
                                        params=request.query_params, timeout=30.0)
        except httpx.RequestError as e:
            return JSONResponse({"error": str(e)}, status_code=502)

        if spec:
            resp_body = None
            try:
                resp_body = resp.json()
            except Exception:
                resp_body = resp.text
            for v in check_response(method, full, resp.status_code, resp_body, spec):
                print_violation(svc.name, method, full, v)

        if recorder:
            rec_body = None
            try:
                rec_body = resp.json()
            except Exception:
                rec_body = resp.text
            recorder.record(method, full, dict(request.headers), body,
                           resp.status_code, dict(resp.headers), rec_body)

        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

    return app


def _pick_service(path: str, by_prefix: dict[str, ServiceConfig]) -> ServiceConfig | None:
    best = (-1, None)
    for prefix, svc in by_prefix.items():
        if path.startswith(prefix) and len(prefix) > best[0]:
            best = (len(prefix), svc)
    return best[1]