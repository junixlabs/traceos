#!/usr/bin/env python3
"""Build the GitHub Pages site: a landing page plus a live explorer per model.

The site exists for the one thing a repository page cannot show — the explorer
running against a real model. Everything on it is generated from the models in this
repository, so it cannot describe a version of TraceOS that does not exist.

    python3 tools/site.py --out site
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import engine as T
import explore

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/junixlabs/traceos"

MODELS = [
    (
        "traceos",
        "examples/traceos-itself",
        "TraceOS modelled in TraceOS",
        "The repository describing itself. Four flows, nineteen evidence references, "
        "validated in CI like any other model.",
        [{}],
    ),
    (
        "ecommerce",
        "examples/ecommerce",
        "E-commerce reference model",
        "Touches every entity: a human decision, a scheduled flow, a two-tenant "
        "feature flag, event fan-out, independent partial-failure outcomes.",
        [{"tenant": "a", "env": "production"}, {"tenant": "b", "env": "production"}],
    ),
]


def landing(cards: list[tuple[str, str, str, str]]) -> str:
    now = dt.datetime.now(dt.UTC)
    items = "\n".join(
        f"""    <a class="card" href="{href}">
      <h2>{html.escape(title)}</h2>
      <p>{html.escape(blurb)}</p>
      <span class="meta">{html.escape(meta)}</span>
    </a>"""
        for href, title, blurb, meta in cards
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TraceOS — live models</title>
<meta name="description" content="Trace before change. Reconcile after change.
Live TraceOS models, rendered from the repository.">
<style>
:root {{ --bg:#fbfaf8; --card:#fff; --ink:#1a1a1c; --muted:#7b7b85; --line:#e4e2dd;
  --accent:#3f7fbf; }}
@media (prefers-color-scheme:dark) {{ :root {{ --bg:#141416; --card:#1c1c20;
  --ink:#eceaea; --muted:#8e8e99; --line:#2c2c32; --accent:#6ea8e0; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
.wrap {{ max-width:760px; margin:0 auto; padding:64px 24px 80px }}
h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-.01em }}
.tagline {{ color:var(--muted); font-size:17px; margin:0 0 28px }}
.lede {{ margin:0 0 36px; max-width:62ch }}
.card {{ display:block; background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:18px 20px; margin:0 0 14px; text-decoration:none;
  color:inherit; transition:border-color .12s }}
.card:hover {{ border-color:var(--accent) }}
.card h2 {{ font-size:17px; margin:0 0 6px; color:var(--accent) }}
.card p {{ margin:0 0 8px; color:var(--ink) }}
.meta {{ font-size:12px; color:var(--muted);
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace }}
.note {{ color:var(--muted); font-size:13px; margin-top:32px; max-width:62ch }}
a.plain {{ color:var(--accent) }}
footer {{ margin-top:44px; padding-top:18px; border-top:1px solid var(--line);
  color:var(--muted); font-size:13px }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px }}
</style></head><body><div class="wrap">

<h1>TraceOS</h1>
<p class="tagline">Trace before change. Reconcile after change.</p>

<p class="lede">A semantic layer that lets a coding agent see a system as behavior
rather than as files. These are the reference models, rendered by the engine in
<a class="plain" href="{REPO}">the repository</a>. Each page is generated on every
push to <code>main</code>, so nothing here can describe a version that does not
exist.</p>

{items}

<p class="note">Each page is a <strong>view</strong>, not a source of truth. Effective
reality, impact, coverage and integrity are computed by the engine and embedded as
results — no traversal runs in the browser, so there is no second implementation to
drift from the engine.</p>

<p class="note"><strong>A page showing <code>uncertain</code> is not a broken
page.</strong> Confidence is computed from when each reference was last checked and
whether the artifact has changed since. Edit a file a model cites and its confidence
falls here on the next push, with nobody touching the model — that is the mechanism,
not a fault. <code>integrity: UNCERTAIN</code> likewise usually means there are
repository files the model does not cover, which is the normal state of a model that
is honest about its edges.</p>

<footer>
Built {now:%Y-%m-%d} · <a class="plain" href="{REPO}">source</a> ·
<a class="plain" href="{REPO}/blob/main/docs/semantic-specification.md">specification</a> ·
<a class="plain" href="{REPO}/blob/main/docs/decisions/README.md">decisions</a>
</footer>
</div></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--repo", default=str(ROOT))
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cards = []

    for slug, rel, title, blurb, contexts in MODELS:
        model_dir = ROOT / rel
        repo_files_path = model_dir / "repo-files.txt"
        repo_files = None
        if repo_files_path.is_file():
            listed = repo_files_path.read_text().splitlines()
            repo_files = [line.strip() for line in listed if line.strip()]

        page = explore.build(model_dir, pathlib.Path(args.repo), repo_files, contexts)
        (out / f"{slug}.html").write_text(page, encoding="utf-8")

        model = T.Model(model_dir)
        meta = (
            f"{len(model.flows)} flows · {len(model.nodes)} nodes · "
            f"{len(model.assertions)} assertions · {len(model.observations)} observations"
        )
        cards.append((f"{slug}.html", title, blurb, meta))
        print(f"{out / slug}.html  ({meta})")

    (out / "index.html").write_text(landing(cards), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"{out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
