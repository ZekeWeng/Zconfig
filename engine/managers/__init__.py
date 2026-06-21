"""Package-manager adapter registry with drop-in discovery.

A new adapter is added by dropping one file in this directory that subclasses
``PackageManager`` and decorates itself with ``@register``. On import this
module walks the package and imports every sibling module, so registration
happens with no edits to the core engine — satisfying the manifest's
"adding an adapter is dropping in one file" requirement.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TypeVar

from ..ports import CommandRunner, ManagerProvider, PackageManager

_REGISTRY: dict[str, type[PackageManager]] = {}

_ManagerT = TypeVar("_ManagerT", bound=PackageManager)


def register(cls: type[_ManagerT]) -> type[_ManagerT]:
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} must define a class-level `name`")
    _REGISTRY[name] = cls
    return cls


def _discover() -> None:
    for module in pkgutil.iter_modules(__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{__name__}.{module.name}")


class Registry(ManagerProvider):
    """Composition-root provider: instantiates a registered adapter on demand."""

    def __init__(self, runner: CommandRunner) -> None:
        _discover()
        self._runner = runner
        self._cache: dict[str, PackageManager] = {}

    def get(self, name: str) -> PackageManager | None:
        if name not in _REGISTRY:
            return None
        if name not in self._cache:
            self._cache[name] = _REGISTRY[name](self._runner)
        return self._cache[name]

    def all(self) -> list[PackageManager]:
        return [self.get(name) for name in sorted(_REGISTRY)]  # type: ignore[misc]

    @staticmethod
    def known_names() -> list[str]:
        _discover()
        return sorted(_REGISTRY)
