"""TraceOS - a semantic reasoning framework.

Lets AI agents trace semantic impact before a change and reconcile the model
with reality after it.

`main` and `parse_context` stay importable from the package for embedders. They
are resolved lazily: importing `.cli` at module scope put it in `sys.modules`
before `python3 -m traceos.cli` executed it, and Python printed a RuntimeWarning
about unpredictable behaviour into the user's output on every such run.
"""

__all__ = ["main", "parse_context"]


def __getattr__(name: str):
    if name in __all__:
        from . import cli

        return getattr(cli, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
