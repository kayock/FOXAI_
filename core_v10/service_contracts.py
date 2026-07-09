from __future__ import annotations
from typing import Any

try:
    from pydantic import BaseModel, Field
except Exception:
    BaseModel = object
    Field = None

if Field:
    class ServiceContract(BaseModel):
        key: str
        name: str
        kind: str = "service"
        department: str = "Engineering"
        provides: list[str] = Field(default_factory=list)
        consumes: list[str] = Field(default_factory=list)
        methods: list[str] = Field(default_factory=list)
        version: str = "1.0"
        status: str = "unknown"

    class ServiceHealth(BaseModel):
        key: str
        ok: bool
        status: str
        message: str = ""
        data: dict[str, Any] = Field(default_factory=dict)
else:
    class ServiceContract(dict):
        pass

    class ServiceHealth(dict):
        pass


# ---------------------------------------------------------------------------
# CM v6.2 compatibility exports
# ---------------------------------------------------------------------------
# service_container.py expects ServiceContract and ServiceHealth.
# These compatibility models keep the Service Container importable while the
# newer service contract schema continues to evolve.

try:
    BaseModel
except NameError:
    from pydantic import BaseModel, Field
    from typing import Any


class ServiceHealth(BaseModel):
    key: str = ""
    ok: bool = True
    status: str = "ready"
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ServiceContract(BaseModel):
    key: str
    kind: str = "service"
    provides: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    health: ServiceHealth | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


try:
    __all__
except NameError:
    __all__ = []

for _name in ["ServiceHealth", "ServiceContract"]:
    if _name not in __all__:
        __all__.append(_name)

