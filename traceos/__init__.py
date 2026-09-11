"""TraceOS - a semantic reasoning framework.

Lets AI agents trace semantic impact before a change and reconcile the model
with reality after it.

The package keeps the `traceos` module name the command line always had, so
`import traceos` keeps working for embedders. The test suite imports the
submodules directly (`from traceos import cli, engine`), so it is not a reason
to keep this re-export - an embedder is.
"""

from .cli import main, parse_context

__all__ = ["main", "parse_context"]
