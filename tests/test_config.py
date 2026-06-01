from pathlib import Path

import pytest
import yaml

from mockyard.config import EdgeMockConfig, ServiceConfig, load_config


def test_valid_config(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}')

    cfg = EdgeMockConfig(
        target="a",
        services=[
            ServiceConfig(name="a", openapi=str(api), path="/a", port=8001, command="echo hi"),
            ServiceConfig(name="b", openapi=str(api), path="/b", port=8002),
        ],
    )
    assert cfg.gateway_port == 8000
    assert cfg.target == "a"
    assert len(cfg.services) == 2


def test_port_conflict(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}')

    with pytest.raises(ValueError, match="port conflict"):
        EdgeMockConfig(
            target="a",
            services=[
                ServiceConfig(name="a", openapi=str(api), path="/a", port=8000),
                ServiceConfig(name="b", openapi=str(api), path="/b", port=8000),
            ],
        )


def test_path_conflict(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}')

    with pytest.raises(ValueError, match="duplicate path"):
        EdgeMockConfig(
            target="a",
            gateway_port=9000,
            services=[
                ServiceConfig(name="a", openapi=str(api), path="/dup", port=8001),
                ServiceConfig(name="b", openapi=str(api), path="/dup", port=8002),
            ],
        )


def test_target_not_found(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}')

    with pytest.raises(ValueError, match="not in services"):
        EdgeMockConfig(
            target="nonexistent",
            services=[ServiceConfig(name="a", openapi=str(api), path="/a", port=8001)],
        )


def test_load_from_yaml(tmp_path: Path):
    api = tmp_path / "api.json"
    api.write_text('{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}')
    cfg_file = tmp_path / "mockyard.yaml"
    cfg_file.write_text(yaml.dump({
        "gateway_port": 9000,
        "target": "x",
        "services": [{"name": "x", "openapi": str(api), "path": "/x", "port": 9001, "command": "uvicorn app:app"}],
    }))

    cfg = load_config(cfg_file)
    assert cfg.gateway_port == 9000
    assert cfg.target == "x"


def test_missing_openapi_file(tmp_path: Path):
    cfg_file = tmp_path / "mockyard.yaml"
    cfg_file.write_text(yaml.dump({
        "target": "x",
        "services": [{"name": "x", "openapi": "/does/not/exist.json", "path": "/x", "port": 8001}],
    }))
    with pytest.raises(ValueError, match="not found"):
        load_config(cfg_file)