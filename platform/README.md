# KST Platform

A platform that brings R and Python packages for knowledge space theory
(`kst`, `pks`, `DAKS`, later `learning_spaces`) into one environment: users
store response data, run analyses and review results without programming
in each package separately.

## Layout

| Folder | Contents |
|---|---|
| `core/ksplatform/` | Framework-independent core |
| `core/ksplatform/analyses/` | One module per analysis, discovered automatically |
| `core/ksplatform/runners/` | How analyses are executed: `Rscript`, in-process Python |
| `r/` | One R script per analysis, JSON in and out; shared helpers in `common.R` |
| `tests/` | pytest suite |
| `examples/data/` | Small example datasets |
| `docs/` | Design decisions and how-to guides |

Planned: a web application (framework not chosen yet), a literature tracking
component, and integration with the group's knowledge graph.

## Available analyses

| Id | Package | Input | Output |
|---|---|---|---|
| `daks.iita` | DAKS | responses | prerequisite relation |
| `kst.space` | kst | prerequisite relation | knowledge space |

Adding one: [docs/adding-an-analysis.md](docs/adding-an-analysis.md).

## Running

All commands are run from the `platform/` folder of the shared repository.

With Docker (R, packages and Python included):

```bash
docker compose run --rm app
```

Locally, with R and the packages `jsonlite`, `kst`, `pks` and `DAKS` installed:

```bash
pip install -e ".[dev]"
pytest
```

## Example

```python
from ksplatform import PrerequisiteRelation, ResponseDataset, run_analysis

dataset = ResponseDataset.from_csv_file("examples/data/chain_example.csv")
iita = run_analysis("daks.iita", {"responses": dataset}, {"version": 2})
iita.result["pairs"]        # [["a", "b"], ["a", "c"], ["b", "c"]]
iita.environment            # R and package versions
iita.input_hashes           # which exact data it ran on

relation = PrerequisiteRelation.from_payload(iita.result)
space = run_analysis("kst.space", {"relation": relation})
space.result["states"]      # one 0/1 row per knowledge state
```

## Conventions

- A pair `(a, b)` means *a is a prerequisite of b*: whoever masters b also masters a.
- Structures always carry the full list of items, so isolated items are not lost.
- Code, names and comments are in English.
