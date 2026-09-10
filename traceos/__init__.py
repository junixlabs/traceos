"""TraceOS - a semantic reasoning framework.

Lets AI agents trace semantic impact before a change and reconcile the model
with reality after it.

The package deliberately keeps the `traceos` module name the command line
always had, so `import traceos` keeps working for the test suite and for
embedders.
"""

from .cli import main, parse_context

__all__ = ["main", "parse_context"]
