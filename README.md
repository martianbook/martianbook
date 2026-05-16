<!-- LOGO -->
<p align="center">
<img width="350" alt="martian" src="https://github.com/user-attachments/assets/11188c0e-5e79-48ca-9b5a-2750b59c86da" />

</p>


<p align="center">
  <strong>Transform ordinary codebases into explainable execution artifacts.</strong>
</p>


<p align="center">
  Martian captures how software behaves while it runs — function calls,
  outputs, artifacts, logs, execution flow, runtime metadata, and
  relationships — then compiles them into rich interactive mission reports
  called <strong>MartianBooks</strong>.
</p>

<p align="center">
Write normal code.<br>
Martian observes.<br>
No notebooks required.
</p>

<p align="center">
  👨‍🚀 📈 👁️ 😨🔥
</p>

---


## Explain It Like I'm A Little Martian

Imagine your code is a space mission.

Tiny astronauts are running around doing jobs 👨‍🚀👨‍🚀👨‍🚀👨‍🚀

One astronaut loads data.  
One astronaut cleans things.  
One astronaut makes a chart 📈  
One astronaut accidentally catches on fire 😨🔥

Martian floats nearby and silently watches the chaos.

It remembers:

- who did what
- who called whom
- what got created
- what got printed
- what exploded
- how long everything took

Then Martian turns the whole mission into a MartianBook so humans can explore what happened afterward and pretend they completely understood it.

You write normal code. Martian just observes 👁️

No notebook rituals required.

---

## Why?

Developers often end up choosing between:

**Clean projects**

```
src/
models/
utils/
main.py
```

and:

```
analysis_FINAL_v7_REAL_FINAL.ipynb
```

because notebooks are easy to explain, visualize, and share.

Martian preserves normal software structure while giving you notebook-like explainability after execution. It does not force cell-based workflows. It generates explainable execution artifacts from ordinary projects.

---

## Installation

### Recommended — uv tool (installs `martian` as a global command)

```bash
uv tool install martianbook
```

This registers `martian` as a bare command available anywhere in your terminal.

### pip

```bash
pip install martianbook
```

### Development (from source)

```bash
git clone https://github.com/yourname/martianbook
cd martianbook
uv tool install .
```

Verify:

```bash
martian --version
```

---

## Quick Start

Decorate your functions. Run your script. Done.

```python
# main.py
import martianbook as martian

@martian.capture
def load_data(path: str):
    """Loads raw CSV data and validates schema."""
    print(f"Loading {path}...")
    return {"rows": 1200}

@martian.capture
def clean_data(dataset: dict):
    """Removes nulls and validates required columns."""
    print(f"Cleaning {dataset['rows']} rows...")
    return {**dataset, "rows": dataset["rows"] - 14}

@martian.section("Pipeline")
def run():
    """Full pipeline from ingestion to output."""
    data  = load_data("data/raw.csv")
    clean = clean_data(data)

if __name__ == "__main__":
    run()
```

Run with Martian:

```bash
cd examples
martian run main.py
```

Output:

```
  ╔╦╗╔═╗╦═╗╔╦╗╦╔═╗╔╗╔
  ║║║╠═╣╠╦╝ ║ ║╠═╣║║║
  ╩ ╩╩ ╩╩╚═ ╩ ╩╩ ╩╝╚╝  v0.1.0

  Running: main.py

  Initializing mission...
Loading data/raw.csv...
Cleaning 1200 rows...
  Capturing telemetry...

  Mission complete. 2 functions captured  12.3ms
  Report → .martian/report.json
```

---

## CLI

```bash
cd examples

martian run main.py                    # execute and capture
martian run main.py --inspect          # run and print summary
martian inspect                        # print summary of last run
martian serve                          # open MartianBook in browser
martian export                         # export standalone HTML
martian export --output report.html    # export to specific path
```

---

## Decorators

### `@martian.capture`

Instruments a function. Martian records its source, docstring, arguments, stdout, return value, timing, exceptions, and any files it produces.

```python
@martian.capture
def train_model(data):
    """Trains the model on cleaned data."""
    ...
```

### `@martian.skip`

Function executes normally. Martian ignores it entirely. Useful for debug helpers, internal utilities, or noisy functions you don't want in the report.

```python
@martian.skip
def debug_dump():
    print("internal state...")
```

### `@martian.section`

Groups all functions called inside this one under a named section in MartianBook.

```python
@martian.section("Data Pipeline")
def run_pipeline():
    """Full pipeline from ingestion to output."""
    load_data()
    clean_data()
    train_model()
```

---

## Artifact Detection

Martian automatically detects files produced during execution. Save anything to `.martian/artifacts/` and it appears in the report linked to the function that created it.

```python
@martian.capture
def plot_results(data):
    """Plots distribution of results."""
    plt.savefig(".martian/artifacts/distribution.png")
```

Supported types: PNG, SVG, JPG, CSV, JSON, TXT, and any other file format.

---

## Generated Structure

```
.martian/
├── report.json       ← full execution IR
└── artifacts/        ← files produced during the run
```

---

## Intermediate Representation

Martian uses a language-independent runtime schema. All adapters produce the same `report.json`. All renderers consume only that file.

```json
{
  "martian_version": "0.1.0",
  "mission": {
    "entry_point": "main.py",
    "duration_ms": 104.3,
    "status": "success"
  },
  "execution": [
    {
      "name": "load_data",
      "duration_ms": 50.3,
      "stdout": ["Loading data/raw.csv..."],
      "children": ["clean_data"]
    }
  ]
}
```

This separation allows HTML renderers, desktop apps, hosted viewers, VSCode integrations, and future language adapters to all consume the same format.

---

## Design Principles

- write ordinary software
- avoid notebook-first workflows
- preserve explainability
- keep instrumentation independent from rendering
- keep schemas language-agnostic
- build bicycles before space stations

---

## Core Ideas

### Mission

A single execution run. One `martian run` = one mission. Captures execution order, telemetry, stdout/stderr, return summaries, artifacts, exceptions, dependencies, and environment metadata.

### Execution Nodes

Each captured function becomes a node in the execution tree, linked to its parent and children. The tree is built automatically from the call stack — no manual wiring required.

### MartianBook

A rendered execution experience built from captured runtime information. Each function becomes a cell with four layers: text (docstring), source code, outputs, and artifacts.

---

## Current Status

✅ Python runtime instrumentation  
✅ Execution tree generation  
✅ Function-level telemetry  
✅ stdout/stderr capture  
✅ Runtime duration tracking  
✅ Exception capture  
✅ Artifact detection  
✅ Return value summaries  
✅ Dependency relationships  
✅ JSON intermediate representation  
✅ Modular adapter architecture  
✅ CLI (`martian run`, `martian inspect`, `martian serve`, `martian export`)

---

## Roadmap

**Near-term**

- MartianBook renderer (full styled UI)
- Execution graph visualization
- Collapsible function timelines
- Artifact previews in browser
- HTML export

**Future**

- Rust adapter
- C++ adapter
- JavaScript adapter
- Desktop application
- VSCode integration
- Hosted mission viewer
- Multi-language execution support

**Far future**

```bash
martian build universe/
```

Results may vary.

---

## Author

Built by Andrew Garcia, Ph.D. (known in select computational sectors as Andrew "F*rking" Ryan Garcia)

Martian started with a simple question:

Why should developers have to choose between clean software architecture and explainable notebooks?

Martian explores a different path:

Write ordinary software.

Observe execution.

Generate explainable artifacts afterward.

---

## License

MIT
