"""zconfig engine — declarative, cross-platform software management.

Hexagonal layout: ``domain`` is the pure core, ``ports`` the interfaces,
``managers`` + ``shell``/``console``/``toml_io``/``lockfile``/``platform`` the
adapters, ``services`` the application layer, ``commands`` the CLI command
table, and ``__main__`` the composition root that wires concretes together.
"""

__version__ = "0.1.0"
