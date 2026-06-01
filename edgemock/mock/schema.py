import hashlib
from typing import Any

from faker import Faker


def _seeded_faker(entity_id: str) -> Faker:
    seed = int(hashlib.sha256(entity_id.encode()).hexdigest()[:8], 16)
    f = Faker()
    f.seed_instance(seed)
    return f


def _resolve(schema: dict, ref: str, components: dict) -> dict:
    if ref.startswith("#/components/schemas/"):
        name = ref.split("/")[-1]
        resolved = components.get("schemas", {}).get(name)
        if not resolved:
            raise ValueError(f"schema '{name}' not found")
        return resolved
    raise ValueError(f"cant resolve {ref}")


def _gen_value(schema: dict, components: dict, eid: str) -> Any:
    if "$ref" in schema:
        schema = _resolve(schema, schema["$ref"], components)

    fmt = schema.get("format", "")
    enum_vals = schema.get("enum")
    if enum_vals:
        return enum_vals[0]

    stype = schema.get("type")
    if stype == "string":
        f = _seeded_faker(eid)
        if fmt == "uuid":
            return str(f.uuid4())
        elif fmt == "email":
            return f.email()
        elif fmt == "date-time":
            return f.iso8601()
        elif fmt == "date":
            return f.date()
        elif fmt == "uri":
            return f.url()
        else:
            return f.name()
    elif stype == "integer":
        f = _seeded_faker(eid)
        lo = schema.get("minimum")
        hi = schema.get("maximum")
        if lo is not None and hi is not None:
            return f.pyint(min_value=lo, max_value=hi)
        return f.pyint(min_value=0, max_value=999)
    elif stype == "number":
        f = _seeded_faker(eid)
        return round(f.pyfloat(min_value=0, max_value=999), 2)
    elif stype == "boolean":
        return True
    elif stype == "array":
        items = schema.get("items", {})
        return [_gen_value(items, components, f"{eid}[0]")]
    elif stype == "object":
        result = {}
        for name, prop in schema.get("properties", {}).items():
            result[name] = _gen_value(prop, components, f"{eid}.{name}")
        return result
    else:
        return None


def generate(schema: dict, components: dict | None = None, entity_id: str = "root") -> Any:
    return _gen_value(schema, components or {}, entity_id)