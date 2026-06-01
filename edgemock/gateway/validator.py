import re
from typing import Any

from jsonschema import validate, ValidationError
from jsonschema.validators import validator_for


def check_request(method: str, path: str, query: dict[str, str], body: Any | None, spec: dict) -> list[str]:
    issues = []
    op = _find_operation(method, path, spec)
    if not op:
        return issues

    for param in op.get("parameters", []):
        if param.get("in") == "query":
            name = param["name"]
            schema = param.get("schema", {})
            if name in query:
                err = _type_check(query[name], schema)
                if err:
                    issues.append(f"query '{name}': {err}")

    if body is not None and "requestBody" in op:
        content = op["requestBody"].get("content", {})
        schema = content.get("application/json", {}).get("schema")
        if schema:
            resolved = _resolve_refs(schema, spec.get("components", {}))
            try:
                validate(body, resolved)
            except ValidationError as e:
                issues.append(e.message)

    return issues


def check_response(method: str, path: str, status: int, body: Any | None, spec: dict) -> list[str]:
    issues = []
    op = _find_operation(method, path, spec)
    if not op:
        return issues

    resp = op.get("responses", {}).get(str(status)) or op.get("responses", {}).get("default")
    if not resp:
        return issues

    content = resp.get("content", {})
    schema = content.get("application/json", {}).get("schema")
    if body is not None and schema:
        resolved = _resolve_refs(schema, spec.get("components", {}))
        try:
            validate(body, resolved)
        except ValidationError as e:
            issues.append(e.message)

    return issues


def _find_operation(method: str, path: str, spec: dict):
    paths = spec.get("paths", {})
    if path in paths:
        return paths[path].get(method.lower())
    for spec_path, methods in paths.items():
        pattern = re.sub(r"\{(\w+)\}", r"[^/]+", spec_path)
        if re.fullmatch(pattern, path):
            return methods.get(method.lower())
    return None


def _type_check(value: str, schema: dict) -> str | None:
    t = schema.get("type")
    try:
        match t:
            case "integer":
                int(value)
            case "number":
                float(value)
            case "boolean":
                if value.lower() not in ("true", "false", "1", "0"):
                    raise ValueError
        return None
    except (ValueError, TypeError):
        return f"expected {t}, got '{value}'"


def _resolve_refs(schema: dict, components: dict) -> dict:
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/components/schemas/"):
            name = ref.split("/")[-1]
            resolved = components.get("schemas", {}).get(name, {})
            return _resolve_refs(resolved, components)
    result = {}
    for k, v in schema.items():
        if isinstance(v, dict):
            result[k] = _resolve_refs(v, components)
        elif isinstance(v, list):
            result[k] = [_resolve_refs(i, components) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result