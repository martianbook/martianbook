<!-- LOGO -->
<p align="center">
  <img width="180" alt="Martian astronaut logo" src="./assets/martian-logo.svg" />
</p>

<h1 align="center">👨‍🚀 Martian</h1>

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

## Explain It Like I'm A Child from Mars

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

You write normal code.

Martian just observes 👁️

No notebook rituals required.

---


## Why?

Developers often end up choosing between:

**Clean projects**

```text
src/
models/
utils/
main.py
```

and:

```text
analysis_FINAL_v7_REAL_FINAL.ipynb
```

because notebooks are easy to explain, visualize, and share.

Martian aims to preserve normal software structure while giving you notebook-like explainability after execution.

Martian does not force cell-based workflows.

It generates explainable execution artifacts from ordinary projects.

---

## Core Ideas

Martian is built around three concepts:

### Mission

A single execution run.

```bash
martian build main.py
```

A mission captures:

- execution order
- runtime telemetry
- stdout/stderr
- return summaries
- generated artifacts
- exceptions
- dependencies
- environment metadata

---

### Execution Nodes

Each captured function becomes a node:

```python
@martian.capture
def clean_data(dataset):
    print("Cleaning rows...")
    return cleaned
```

Martian records:

- source code
- docstrings
- arguments
- runtime duration
- outputs
- child relationships
- artifacts

---

### MartianBook

A rendered execution experience built from captured runtime information.

Conceptually:

```text
[Text]
[Source]
[Outputs]
[Artifacts]
```

MartianBooks allow code to become explorable.

---

## Installation

Using uv:

```bash
uv add martianbook
```

Or:

```bash
pip install martianbook
```

---

## Quick Start

```python
import martianbook as martian
from martianbook.adapters.python.capture import init_session
from martianbook.adapters.python import build_report
from martianbook.core.serialization import save

init_session()


@martian.capture
def load_data():

    """
    Load and validate input data.
    """

    print("Loading...")
    return {"rows":1200}


@martian.capture
def process(data):

    """
    Clean and process records.
    """

    print("Processing...")
    return {"clean":True}


@martian.section("Pipeline")
def run():

    data=load_data()
    process(data)


run()

report=build_report(
    entry_point="main.py",
    started_at="...",
    start_perf=0
)

save(report,".martian/report.json")
```

Run:

```bash
python main.py
```

Output:

```text
=== Martian Mission Starting ===

Loading...
Processing...

=== Mission Complete ===
Captured 2 functions

Report saved to .martian/report.json
```

---

## Decorators

### Capture execution

```python
@martian.capture
def train_model():
    ...
```

Captures:

- source code
- arguments
- outputs
- runtime
- exceptions
- return summaries
- artifacts

---

### Skip functions

```python
@martian.skip
def internal_helper():
    ...
```

Function executes normally.

Martian ignores it.

Useful for:

- debug helpers
- utility wrappers
- noisy internal code

---

### Group into sections

```python
@martian.section("Data Pipeline")
def run_pipeline():
    ...
```

Groups downstream execution into logical sections.

---

## Captured Artifacts

Martian automatically detects newly produced files.

Examples:

- PNG
- SVG
- CSV
- JSON
- text outputs

```python
plt.savefig(".martian/artifacts/chart.png")
```

Artifacts become linked execution outputs.

---

## Generated Structure

```text
.martian/

    report.json
    artifacts/
```

---

## Intermediate Representation

Martian uses a language-independent runtime schema.

Example:

```json
{
  "mission":{
    "entry_point":"main.py"
  },

  "execution":[
    {
      "name":"load_data",
      "duration_ms":50.3,
      "children":["clean_data"]
    }
  ]
}
```

Renderers consume only this schema.

This separation allows:

- HTML renderers
- desktop apps
- hosted viewers
- VSCode integrations
- future language adapters

---

## Design Principles

Martian follows a few rules:

- write ordinary software
- avoid notebook-first workflows
- preserve explainability
- keep instrumentation independent from rendering
- keep schemas language-agnostic
- build bicycles before space stations

---

## Current Status

Current support:

- Python runtime instrumentation
- decorators
- execution trees
- runtime telemetry
- artifact tracking
- JSON serialization

Planned:

- MartianBook renderer
- local web viewer
- `martian serve`
- Rust adapters
- C++ adapters
- JavaScript adapters


---

## Author

Built by Andrew Garcia, Ph.D.  (a.k.a Andrew Effing Ryan Garcia in select computational sectors)

Martian started with a simple question:

Why should developers have to choose between clean software architecture and explainable notebooks?

Martian explores a different path:

Write ordinary software.

Observe execution.

Generate explainable artifacts afterward.

---

## Roadmap

Near-term:

- MartianBook renderer
- local web UI
- `martian serve`
- execution graph visualization
- collapsible function timelines
- artifact previews
- HTML export

Future:

- Rust adapter
- C++ adapter
- JavaScript adapter
- desktop application
- VSCode integration
- hosted mission viewer
- multi-language execution support

Far future:

```bash
martian build universe/
```

Results may vary.

---

## Current Capabilities

Martian currently supports:

✅ Python runtime instrumentation  
✅ execution tree generation  
✅ function-level telemetry  
✅ stdout/stderr capture  
✅ runtime duration tracking  
✅ exception capture  
✅ artifact detection  
✅ return value summaries  
✅ dependency relationships  
✅ JSON intermediate representation  
✅ modular adapters

Planned expansions:

🚀 MartianBook renderer  
🚀 local mission viewer  
🚀 CLI workflow improvements  
🚀 additional language adapters

---



## License

MIT