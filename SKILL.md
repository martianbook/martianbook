# SKILL: MartianBook
> Attach this file to any LLM conversation to get accurate help with MartianBook.

## What is MartianBook?

MartianBook is a tool that transforms ordinary Python scripts into interactive
execution reports. You decorate the functions you want to explain, run your
script with `martian`, and get a rich HTML document showing syntax-highlighted
source code, outputs, plots, and execution flow — without ever touching a notebook.

**The core idea:** write normal Python. Martian observes. No Jupyter required.

---

## Installation

```bash
uv add martianbook
```

Install martianbook into your project environment alongside your own deps.
Never install it as a global tool — it needs to see your packages (torch,
numpy, pandas, etc).

```bash
# Add martianbook alongside your own deps in one shot
uv add martianbook numpy matplotlib torch
```

Or with pip:

```bash
pip install martianbook
```

For local development of martianbook itself:

```toml
[tool.uv.sources]
martianbook = { path = "../martianbook", editable = true }
```

```bash
uv sync
```

---

## Running

```bash
uv run martian main.py              # run a single script
uv run martian "examples/*.py"      # wildcard — runs all matching scripts
uv run martian go main.py           # explicit subcommand (same thing)
uv run martian main.py --inspect    # run and print terminal summary
uv run martian inspect              # print summary of last run
uv run martian serve                # open MartianBook in browser at localhost:7420
uv run martian export               # export standalone HTML file
uv run martian export -o out.html   # export to specific path
```

**Alias shortcut** — add to `~/.bashrc` or `~/.zshrc` to drop `uv run`:

```bash
alias martian="uv run martian"
```

Then just:

```bash
martian main.py
martian serve
martian export
```

---

## The Four Decorators

These are the only things a user ever adds to their code.

### `@martian.capture`

Instruments a function. MartianBook will show its docstring, source code,
arguments, stdout, return value, timing, and any files it produces.

**Only decorate functions you want to appear in MartianBook.**
Everything else runs normally and stays invisible.

```python
import martianbook as martian

@martian.capture
def load_data(path: str):
    """Loads raw CSV data and validates schema."""
    print(f"Loading {path}...")
    return {"rows": 1200}
```

### `@martian.skip`

Function runs normally but Martian completely ignores it.
Use for debug helpers, noisy internals, logging utilities.

```python
@martian.skip
def debug_dump(data):
    print(f"DEBUG: {data}")
```

### `@martian.section`

Groups all captured functions called inside it under a named section
in MartianBook. Think of it as a chapter heading.

```python
@martian.section("Data Pipeline")
def run_pipeline():
    """Full pipeline from ingestion to output."""
    load_data("data/raw.csv")
    clean_data()
    train_model()
```

### `@martian.text`

Attaches a standalone prose block to the function immediately below it
in the decorator stack. Renders above that function's cell in MartianBook.
Stack multiple blocks — they appear top-to-bottom exactly as written in source.

```python
@martian.text("## Data Ingestion")
@martian.text("Loads raw CSV from the data lake and validates schema.")
@martian.capture
def load_data(path: str):
    ...
```

The docstring form is equivalent for a single block — whichever feels natural:

```python
@martian.capture
def load_data(path: str):
    """## Data Ingestion — Loads raw CSV from the data lake."""
    ...
```

For multiple blocks, `@martian.text` is the only option since a function
can only have one docstring.

---

## Docstrings are text blocks

The docstring of a `@martian.capture` function becomes the prose
explanation in MartianBook. Write it for a human reader.

```python
@martian.capture
def clean_data(dataset: dict):
    """
    Removes null rows, strips whitespace from string columns,
    and validates that all required columns are present before
    passing downstream.
    """
    ...
```

No docstring = no text block. The code and output still appear.

---

## Artifacts (plots, files, CSVs)

Save any file to `.martian/artifacts/` during execution and it appears
in MartianBook linked to the function that produced it.
In exported HTML, images are embedded inline (no external dependencies).

```python
@martian.capture
def plot_distribution(data):
    """Plots the distribution of values across all numeric columns."""
    import matplotlib
    matplotlib.use("Agg")   # required for non-GUI environments
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(data, bins=40, color="#7dd3fc")
    ax.set_title("Distribution")
    fig.savefig(".martian/artifacts/distribution.png", dpi=150)
    plt.close(fig)
```

**Critical:** always call `matplotlib.use("Agg")` before importing
`matplotlib.pyplot` in scripts run by Martian. Otherwise matplotlib
tries to open a GUI window and may hang or error.

Supported artifact formats: PNG, SVG, JPG, CSV, JSON, TXT, and any
other file type (shown as a download link).

---

## Generated structure

After running:

```
.martian/
├── report.json         ← full execution IR (language-agnostic)
└── artifacts/          ← files produced during the run (cleared each run)
```

The artifact directory is wiped clean at the start of every `martian` run
so stale files from previous runs never pollute the new report.

---

## Full working example

```python
# main.py
import martianbook as martian
import os

os.makedirs(".martian/artifacts", exist_ok=True)


@martian.text("## Data Ingestion")
@martian.capture
def load_data(path: str):
    """Loads raw CSV data from disk and performs an initial row count."""
    print(f"Loading from {path}...")
    return {"rows": 1200, "cols": 8}


@martian.capture
def clean_data(dataset: dict):
    """Removes null rows and validates required columns are present."""
    print(f"Cleaning {dataset['rows']} rows...")
    removed = 14
    print(f"Removed {removed} null rows.")
    return {**dataset, "rows": dataset["rows"] - removed}


@martian.capture
def plot_summary(dataset: dict):
    """Plots a simple bar summary of dataset dimensions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(["rows", "cols"], [dataset["rows"], dataset["cols"]], color="#7dd3fc")
    ax.set_title("Dataset Summary")
    fig.savefig(".martian/artifacts/summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Plot saved.")


@martian.skip
def debug_dump(data):
    print(f"DEBUG: {data}")


@martian.section("Data Pipeline")
def run():
    """Full pipeline from raw ingestion through visualization."""
    data   = load_data("data/raw.csv")
    clean  = clean_data(data)
    debug_dump(clean)
    plot_summary(clean)


if __name__ == "__main__":
    run()
```

```bash
uv run martian main.py
uv run martian serve
```

---

## What appears in MartianBook

Each `@martian.capture` function becomes a cell with four layers:

```
┌─────────────────────────────────────┐
│ TEXT     docstring or @martian.text │
│ SOURCE   syntax-highlighted source  │
│ OUTPUT   stdout + return value      │
│ ARTIFACT plots, files, images       │
└─────────────────────────────────────┘
```

Cells are collapsible. Functions with no output are collapsed by default.
Parent functions show their children indented beneath them.
`@martian.text` blocks render above the cell they are anchored to.

---

## MartianBook UI

- **Light/dark toggle** — top right corner, `◐` button. Saves preference.
  Defaults to system preference (`prefers-color-scheme`).
- **Expand / collapse all** — controls bar below the header.
- **Collapsible cells** — click any cell header to expand/collapse.
- **Collapsible blocks** — click SOURCE / OUTPUT / ARTIFACT labels to
  collapse individual blocks within a cell independently.
- **Syntax highlighting** — Python source is highlighted with a full
  token palette. Colors adapt automatically to light and dark themes.
- **Section grouping** — `@martian.section` functions show a purple badge
  and group their children visually.
- **Artifacts** — images render inline in the page.
- **Text block editing** — in `serve` mode, text blocks have a textarea
  and save/delete buttons. Edits write back to `report.json` immediately
  so `martian export` always reflects the latest state. Export mode is
  read-only.

---

## Serve mode vs export mode

| | `martian serve` | `martian export` |
|---|---|---|
| Text block editing | ✓ editable | read-only |
| Saves to report.json | ✓ immediately | n/a |
| Add text blocks from UI | ✓ | — |
| Works offline | ✓ (local server) | ✓ (standalone HTML) |
| Shareable | no (localhost only) | ✓ (single file) |

---

## Common mistakes and fixes

**`ModuleNotFoundError` when running**
Martian runs inside your project env. The missing package isn't installed there.
Add it to `pyproject.toml` dependencies and run `uv sync`.

**`0 artifacts` in report even though files were saved**
The artifact dir had stale files from a previous run. This is now auto-fixed
(the dir is cleared before each run). If it persists, manually delete
`.martian/artifacts/` and re-run.

**Plots not appearing / matplotlib GUI error**
Always call `matplotlib.use("Agg")` before `import matplotlib.pyplot as plt`
in any function run under Martian.

**`martian: command not found`**
Either use `uv run martian` or add the alias to your shell config:
```bash
alias martian="uv run martian"
```

**Double-counted artifacts (same plot linked to multiple functions)**
This is handled automatically. Each artifact is assigned to the innermost
function that produced it. Parent functions do not claim children's artifacts.

**Decorated function not appearing in MartianBook**
Check that `@martian.capture` is applied and that the function is actually
called during execution. Decorating a function that is never called produces
no node.

**`@martian.text` block not appearing**
`@martian.text` must be stacked directly above `@martian.capture` (or
above another `@martian.text` that is above `@martian.capture`). It has
no effect if placed above `@martian.skip` or a plain undecorated function.

**`init_session` error**
You should not call `init_session` manually. The `martian` CLI owns session
initialization. Just run `uv run martian main.py`.

---

## What Martian does NOT do

- Does not replace your test suite
- Does not run interactively like Jupyter
- Does not require you to change how you write Python
- Does not capture functions that are not decorated with `@martian.capture`
- Does not support reactive execution (that's Marimo's thing)
- Does not require a server to view exported HTML
- Does not execute code typed into text blocks in serve mode (text only)

---

## Architecture (for LLMs helping with advanced usage)

```
martianbook/
├── core/
│   ├── schema.py          ← IR dataclasses (MartianReport, ExecutionNode,
│   │                          Artifact, TextNode, ...)
│   └── serialization.py   ← JSON round-trip for report.json
├── adapters/
│   └── python/
│       ├── __init__.py    ← build_report()
│       └── capture/
│           ├── decorator.py   ← @capture, @skip, @section, @text
│           ├── wrapper.py     ← execution steps: build_context, pre_register,
│           │                      run, finalize
│           ├── session.py     ← MartianSession, init_session, get_session
│           ├── output.py      ← stdout/stderr Tee capture
│           ├── artifacts.py   ← filesystem snapshot + diff
│           ├── introspect.py  ← source, docstring, args, return summary
│           └── tree.py        ← call stack, ExecutionContext, parent/child wiring
├── renderer/
│   ├── __init__.py        ← render_html(report, editable=False) → standalone HTML
│   ├── cells.py           ← cell, text node, and mission bar HTML rendering
│   ├── embed.py           ← logo + artifact image base64 embedding
│   ├── highlight.py       ← pygments-based syntax highlighting (line-by-line)
│   └── assets/
│       ├── template.html  ← page shell with {{placeholders}}
│       ├── styles.css     ← all CSS (theme vars, layout, cells, highlighting,
│       │                      text nodes)
│       ├── main.js        ← theme toggle, collapse/expand, text node editing
│       └── martian.svg    ← logo
└── cli/
    ├── __init__.py        ← martian CLI (go, serve, inspect, export)
    ├── run.py             ← run_script() — session init, runpy, build_report, save
    ├── serve.py           ← local HTTP server with POST /text and DELETE /text/<id>
    ├── inspect.py         ← terminal summary printer
    └── export.py          ← HTML file export
```

### Key IR types in schema.py

```python
MartianReport      # root — everything in one place
ExecutionNode      # one captured function call → one cell
TextNode           # standalone prose block anchored to an ExecutionNode
Artifact           # file produced during execution
ExceptionRecord    # captured exception with traceback
Section            # named group of ExecutionNodes
```

### TextNode fields worth knowing

```python
TextNode(
    id,                # "txt_a1b2c3d4"
    content,           # the prose string
    source,            # "decorator" | "user"
    anchor_id,         # ExecutionNode.id this renders above
    anchor_index,      # order among texts on same anchor (0 = topmost)
    original_content,  # set on first user edit; None if unedited
    created_at,        # ISO 8601
    edited_at,         # ISO 8601 or None
)
```

### serve mode endpoints

```
GET  /              → full MartianBook HTML (editable=True)
GET  /report.json   → raw report JSON
POST /text          → save or create a TextNode
                      body: { id?, content, anchor_id? }
DELETE /text/<id>   → delete a TextNode
```

The IR (`report.json`) is the only interface between instrumentation and
rendering. The renderer knows nothing about Python. Future adapters (Rust,
C++, JS) produce the same `report.json` schema and work with the same renderer.

---

## Dependencies

| Package | Why |
|---|---|
| `click` | CLI |
| `pygments` | Syntax highlighting in source blocks |

All other functionality uses Python stdlib only.

---

## Version

MartianBook 0.3.0 — Python adapter only.
Rust, C++, and JavaScript adapters are planned.

Built by Andrew Garcia, Ph.D.