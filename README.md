# Mockyard

**Mock your microservice dependencies locally**

Mockyard lets you run one real service while auto-mocking all its dependencies from OpenAPI specs. It starts a gateway that routes requests to either the real service or generated mocks.

## Quick Start

```bash
# clone & install
git clone https://github.com/g3rberr/mockyard.git
cd mockyard
python -m venv .venv && source .venv/bin/activate
pip install -e .

# start — uses examples/mockyard.yaml by default
mockyard target orders
```

```bash
# test it
curl http://localhost:8000/orders        # real orders app
curl http://localhost:8000/users         # auto-mocked users
curl http://localhost:8000/inventory     # auto-mocked inventory
```

## How It Works

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  Client  │ ──▶ │  Gateway     │ ──▶ │  Orders    │ (real, :8001)
│  (curl)  │     │  (:8000)     │     ├────────────┤
└──────────┘     │              │ ──▶ │  Users     │ (mock, :8002)
                 │              │     ├────────────┤
                 │              │ ──▶ │  Inventory │ (mock, :8003)
                 └──────────────┘     └────────────┘
```

- Services **without** a `command` → auto-mocked from their OpenAPI spec
- The **target** service (with `command`) runs as a real process
- The gateway validates requests/responses against OpenAPI schemas
- OpenAPI spec changes trigger hot-reload of mocks

## Your Own Config

```yaml
gateway_port: 8000
target: users

services:
  - name: users
    openapi: specs/users/openapi.json
    path: /users
    port: 8001
    command: "uvicorn users.app:app --port 8001"

  - name: orders
    openapi: specs/orders/openapi.json
    path: /orders
    port: 8002
```

Run with: `mockyard target users`

If a config isn't found in the current directory, `mockyard` falls back to `examples/mockyard.yaml`.

## CLI

| Command | Description |
|---------|-------------|
| `mockyard target <name>` | Start the environment |
| `mockyard validate` | Check config without starting |
| `mockyard status` | List services |
| `mockyard record <session>` | Record interactions *(planned)* |
| `mockyard replay <session>` | Replay a session *(planned)* |

All commands accept `-c <path>` for a custom config file.

## Requirements

- Python ≥ 3.11
- OpenAPI 3.0+ specs (JSON)

## Project

```
mockyard/
├── cli.py              # typer CLI
├── config.py           # pydantic config
├── orchestrator.py     # service lifecycle
├── gateway/
│   ├── app.py          # FastAPI proxy
│   ├── validator.py    # schema validation
│   └── recorder.py     # session recording
├── mock/
│   ├── generator.py    # mock builder from OpenAPI
│   ├── schema.py       # fake data generator
│   └── store.py        # in-memory store
└── ui/
    └── console.py      # logging

examples/
├── mockyard.yaml
├── orders/
├── users/
└── inventory/

tests/
├── test_config.py
├── test_gateway.py
└── test_mock.py
```

## License

MIT
