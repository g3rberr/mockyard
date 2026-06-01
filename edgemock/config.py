from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator, model_validator


class ServiceConfig(BaseModel):
    name: str
    openapi: str
    path: str
    port: int
    command: Optional[str] = None

    @field_validator("openapi", mode="before")
    def ensure_file_exists(cls, v: str) -> str:
        p = Path(v).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"not found: {p}")
        return str(p)

    @field_validator("port")
    def check_port_range(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError(f"port {v} must be between 1024 and 65535")
        return v

    @field_validator("path")
    def check_slash(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError(f"path must start with '/', got {v}")
        return v


class EdgeMockConfig(BaseModel):
    gateway_port: int = 8000
    target: str
    services: list[ServiceConfig]

    @model_validator(mode="after")
    def verify_target(self):
        names = {s.name for s in self.services}
        if self.target not in names:
            raise ValueError(f"target '{self.target}' not in services {names}")
        return self

    @model_validator(mode="after")
    def check_ports(self):
        ports = [self.gateway_port] + [s.port for s in self.services]
        if len(ports) != len(set(ports)):
            raise ValueError(f"port conflict: {ports}")
        return self

    @model_validator(mode="after")
    def check_paths(self):
        paths = [s.path for s in self.services]
        if len(paths) != len(set(paths)):
            raise ValueError(f"duplicate paths: {paths}")
        return self


def load_config(path: Path) -> EdgeMockConfig:
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("config must be a YAML dict")

    return EdgeMockConfig.model_validate(raw)