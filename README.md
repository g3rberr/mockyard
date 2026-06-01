# Mockyard

**Mock your microservice dependencies locally**

Mockyard is a lightweight development tool that helps you mock microservice dependencies in your local environment. It allows you to focus on developing your main service by automatically generating mock responses for dependent services based on their OpenAPI specifications.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Development](#development)
- [License](#license)

## Overview

When developing microservices, you often need to run multiple services locally to test integrations. This can be resource-intensive and complex to set up. Mockyard solves this problem by:

1. **Mocking dependent services** - Automatically generates realistic mock responses based on OpenAPI schemas
2. **Acting as an API gateway** - Routes requests to either real or mock services through a single entry point
3. **Validating requests and responses** - Checks that your service communicates correctly with dependencies
4. **Hot-reloading** - Automatically updates mocks when OpenAPI specifications change

## Features

- **OpenAPI-driven mocks**: Generate mock services directly from OpenAPI 3.0 specifications
- **Smart data generation**: Uses deterministic Faker to create consistent, realistic fake data
- **Request/response validation**: Validates that requests and responses conform to OpenAPI schemas
- **Hot-reload support**: Automatically reloads mock services when OpenAPI specs change
- **In-memory data store**: Mock services maintain state during the session (CRUD operations work)
- **Single gateway endpoint**: Access all services through one unified API gateway
- **Session recording**: Record real API interactions for later replay (planned feature)
- **Flexible configuration**: Easy-to-use YAML configuration for defining services

## Requirements

- Python 3.11 or higher
- OpenAPI 3.0+ specifications for your services (JSON format)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/g3rberr/mockyard.git
cd mockyard
```

### 2. Create a virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Linux/macOS
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
# Install the package and its dependencies
pip install -e .
```

## Quick Start

### 1. Create a configuration file

Create a `mockyard.yaml` file in your project root:

```yaml
gateway_port: 8000
target: orders

services:
  - name: orders
    openapi: ./specs/orders/openapi.json
    path: /orders
    port: 8001
    command: "python -m uvicorn orders.app:app --port 8001"

  - name: users
    openapi: ./specs/users/openapi.json
    path: /users
    port: 8002

  - name: inventory
    openapi: ./specs/inventory/openapi.json
    path: /inventory
    port: 8003
```

### 2. Prepare OpenAPI specifications

Each service needs an OpenAPI 3.0+ specification file. The specification should include:
- Path definitions with HTTP methods
- Request/response schemas
- Component schemas for data models

### 3. Start Mockyard

```bash
mockyard target orders
```

This will:
- Start the API gateway on port 8000
- Launch your `orders` service on port 8001
- Create mock services for `users` (port 8002) and `inventory` (port 8003)

### 4. Test your integration

```bash
# Through the gateway
curl http://localhost:8000/orders/orders
curl http://localhost:8000/users/users
curl http://localhost:8000/inventory/inventory/items
```

## Configuration

Mockyard uses a YAML configuration file (default: `mockyard.yaml`).

### Configuration Structure

```yaml
# Port for the API gateway (default: 8000)
gateway_port: 8000

# Name of the service you're actively developing (will run as real service)
target: orders

# List of all services in your microservice ecosystem
services:
  - name: orders              # Unique service identifier
    openapi: ./specs/orders.json  # Path to OpenAPI specification
    path: /orders             # URL path prefix for this service
    port: 8001                # Port number for this service
    command: "uvicorn app:app" # (Optional) Command to start real service
```

### Configuration Options

#### Root Level

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `gateway_port` | integer | No | 8000 | Port for the API gateway |
| `target` | string | Yes | - | Name of the service being developed |
| `services` | list | Yes | - | List of service configurations |

#### Service Configuration

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | Yes | Unique service identifier |
| `openapi` | string | Yes | Path to OpenAPI JSON specification |
| `path` | string | Yes | URL path prefix (must start with `/`) |
| `port` | integer | Yes | Port number (1024-65535) |
| `command` | string | No | Shell command to start the real service |

### Validation Rules

Mockyard validates your configuration and will error if:
- OpenAPI files don't exist
- Ports conflict with each other or the gateway port
- URL paths are duplicated between services
- The target service is not in the services list
- Port numbers are outside the valid range (1024-65535)
- Paths don't start with `/`

## CLI Commands

### `mockyard target <service>`

Start the development environment with the specified service as the target.

```bash
mockyard target orders
mockyard target orders --config ./config/mockyard.yaml
```

**Options:**
- `-c, --config`: Path to configuration file (default: `mockyard.yaml`)

### `mockyard validate`

Validate the configuration file without starting services.

```bash
mockyard validate
mockyard validate --config ./config/mockyard.yaml
```

### `mockyard status`

Display the current service configuration.

```bash
mockyard status
mockyard status --config ./config/mockyard.yaml
```

### `mockyard record <session>`

Record API interactions to a session file. *(Planned feature)*

```bash
mockyard record my-session
```

### `mockyard replay <session>`

Replay a recorded session. *(Planned feature)*

```bash
mockyard replay my-session
```

## How It Works

### Request Flow

1. **Client sends request** → API Gateway (port 8000)
2. **Gateway routes request** based on URL path prefix
3. **Request is forwarded** to either:
   - Real service (if it's the target service)
   - Mock service (for dependencies)
4. **Response is returned** through the gateway to the client

### Mock Generation

Mock services are automatically generated from OpenAPI specifications:

1. **Schema parsing**: Mockyard reads the OpenAPI spec and extracts endpoint definitions
2. **Route creation**: Creates FastAPI routes for each endpoint
3. **Response generation**: When an endpoint is called:
   - For `GET` requests: Returns stored data or generates fake data from schema
   - For `POST` requests: Stores the submitted data and returns it
   - For `PUT` requests: Updates stored data
   - For `DELETE` requests: Removes stored data
4. **Fake data generation**: Uses deterministic Faker seeded by entity ID for consistency

### Data Persistence

Mock services maintain an in-memory store during the session:
- Data persists across requests within the same session
- Store is cleared when Mockyard stops
- Each collection (resource type) is stored separately

## Architecture

```
┌─────────────────┐
│   Your App      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Gateway   │  (port 8000)
│   (FastAPI)     │
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Orders    │   │   Users     │   │  Inventory  │
│  (Real)     │   │  (Mock)     │   │  (Mock)     │
│  port 8001  │   │  port 8002  │   │  port 8003  │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Components

- **CLI** (`mockyard/cli.py`): Command-line interface using Typer
- **Config** (`mockyard/config.py`): Configuration parsing and validation with Pydantic
- **Orchestrator** (`mockyard/orchestrator.py`): Manages service lifecycle and hot-reload
- **Gateway** (`mockyard/gateway/`): API gateway with routing and validation
- **Mock Generator** (`mockyard/mock/`): Creates mock services from OpenAPI specs
- **UI** (`mockyard/ui/`): Console output and logging

## Examples

### Example Configuration

See `examples/mockyard.yaml` for a complete working example:

```yaml
gateway_port: 8000
target: orders

services:
  - name: orders
    openapi: examples/orders/openapi.json
    path: /orders
    port: 8001
    command: "uvicorn orders.app:app --port 8001"

  - name: users
    openapi: examples/users/openapi.json
    path: /users
    port: 8002

  - name: inventory
    openapi: examples/inventory/openapi.json
    path: /inventory
    port: 8003
```

### Example OpenAPI Specification

See `examples/orders/openapi.json` for a complete example. Key elements:

```json
{
  "openapi": "3.0.3",
  "info": { "title": "Orders Service", "version": "1.0.0" },
  "paths": {
    "/orders": {
      "get": {
        "operationId": "listOrders",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": { "$ref": "#/components/schemas/Order" }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Order": {
        "type": "object",
        "properties": {
          "id": { "type": "string", "format": "uuid" },
          "userId": { "type": "string", "format": "uuid" },
          "total": { "type": "number" },
          "status": { "type": "string", "enum": ["pending", "shipped", "done"] }
        }
      }
    }
  }
}
```

## API Reference

### Gateway Endpoints

The gateway proxies all requests to the appropriate service based on path prefixes defined in the configuration.

**Example:**
```
GET http://localhost:8000/orders/orders/123
→ Routes to orders service at http://127.0.0.1:8001/orders/123

GET http://localhost:8000/users/users/456
→ Routes to users mock at http://127.0.0.1:8002/users/456
```

### Validation

The gateway validates requests and responses against OpenAPI schemas and logs violations:

```
[VIOLATION] orders POST /orders: 'userId' is a required property
[VIOLATION] users GET /users/123: expected integer, got 'abc'
```

## Development

### Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/g3rberr/mockyard.git
cd mockyard

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies (if any)
pip install pytest pytest-asyncio httpx
```

### Running tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=mockyard tests/
```

### Project Structure

```
mockyard/
├── __init__.py
├── cli.py              # CLI commands
├── config.py           # Configuration models
├── orchestrator.py     # Service orchestration
├── gateway/
│   ├── __init__.py
│   ├── app.py          # Gateway FastAPI app
│   ├── recorder.py     # Session recording
│   └── validator.py    # Request/response validation
├── mock/
│   ├── __init__.py
│   ├── generator.py    # Mock service generator
│   ├── schema.py       # Fake data generation
│   └── store.py        # In-memory data store
└── ui/
    ├── __init__.py
    └── console.py      # Console output

examples/
├── mockyard.yaml       # Example configuration
├── orders/
│   └── openapi.json    # Orders service spec
├── users/
│   └── openapi.json    # Users service spec
└── inventory/
    └── openapi.json    # Inventory service spec

tests/
├── __init__.py
├── test_config.py      # Configuration tests
├── test_gateway.py     # Gateway tests
└── test_mock.py        # Mock generator tests
```

### Dependencies

- **typer**: CLI framework
- **pydantic**: Data validation and settings management
- **fastapi**: Modern async web framework
- **uvicorn**: ASGI server
- **httpx**: Async HTTP client
- **faker**: Fake data generation
- **jsonschema**: JSON Schema validation
- **pyyaml**: YAML parsing
- **watchfiles**: File watching for hot-reload
- **rich**: Terminal formatting (optional, for better output)

## License

MIT License - see LICENSE file for details.

---

**Contributing**: Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

**Support**: For issues and feature requests, please use the GitHub issue tracker.