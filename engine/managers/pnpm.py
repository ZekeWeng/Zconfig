"""pnpm global-package adapter."""

from __future__ import annotations

from . import register
from ._node import NodeGlobalManager


@register
class PnpmManager(NodeGlobalManager):
    name = "pnpm"
    cli = "pnpm"
