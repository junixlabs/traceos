# Security

## Reporting a vulnerability

Use GitHub's private reporting: **[Report a vulnerability](https://github.com/junixlabs/traceos/security/advisories/new)**.
Please do not open a public issue for anything exploitable.

Expect an acknowledgement within a week. If a fix is warranted we will work it
through a private advisory and credit you in the release notes unless you prefer
otherwise.

## What is in scope

TraceOS is a specification plus a reference engine that reads a repository and
writes model files. The parts worth reporting on:

- **`tools/traceos.py`, `tools/explore.py`** — the engine reads YAML frontmatter and
  runs `git` against a path you pass with `--repo`. Path traversal out of the model
  directory, argument injection into the `git` invocation, or unsafe YAML handling
  are all in scope.
- **Generated HTML** — `explore` embeds model content into a page. Model text is
  escaped on the way in; a way to break out of that escaping and inject script is in
  scope, because a model may contain text written by someone other than the reader.
- **`observe` and `init`** — both write files. Writing outside the intended
  directory is in scope.

## What is not in scope

- A model that describes a system inaccurately. That is a modelling error, and
  TraceOS is built to surface it as low confidence or a discrepancy rather than to
  prevent it.
- `integrity: UNCERTAIN` on the reference models. That is the intended output, not a
  defect — see `examples/ecommerce/README.md`.
- Denial of service from a deliberately enormous model.

## Handling of repository content

The engine reads the repository under analysis; it never writes to it. Evidence
locators are recorded as text and are never executed. `git` is invoked with a fixed
argument list, never through a shell.
