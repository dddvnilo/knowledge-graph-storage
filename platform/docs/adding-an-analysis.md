# Adding an analysis

An analysis is one function of one package made available on the platform.
Adding one means **adding files only**: no existing file is edited.

## 1. Write the script (R) or the function (Python)

**R:** add `r/<package>_<function>.R`. Use the helpers in `r/common.R`:

```r
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(script_dir, "common.R"))

run_analysis(packages = c("pks"), analysis = function(input) {
  # input$<input name> holds each input's payload, input$params the parameters
  list(...)  # the result; becomes JSON
})
```

`run_analysis` handles reading the input, catching errors and recording the
R and package versions. Input helpers: `response_frame()`,
`aligned_responses()` (responses in a given item order), `relation_matrix()`,
`transitive_closure()`, `structure_matrix()`, `kst_structure()`.

**Python:** write a function `payload -> result dict` and wrap it in a
`PythonRunner`, listing the distributions whose versions are provenance.

## 2. Describe it

Add `core/ksplatform/analyses/<package>_<function>.py`:

```python
from ..runners import RScriptRunner
from ._base import Analysis

ANALYSIS = Analysis(
    id="pks.blim",
    category="data_fit",
    package="pks",
    function="blim",
    description="Fits a basic local independence model.",
    runner=RScriptRunner("pks_blim.R"),
    inputs={"structure": "knowledge_structure", "responses": "responses"},
    output_kind="blim_fit",
    default_params={"method": "ML"},
)
```

`category` is the question the analysis answers; the list is `CATEGORIES`
in `core/ksplatform/analyses/_base.py`. A new kind of question is a new
entry there.

The module is discovered automatically because it defines `ANALYSIS` and its
name does not start with `_`.

## 3. Test it

Add `tests/test_<package>_<function>.py`. Use data where the correct answer
is known, so the test checks the meaning of the result, not just that it ran.
Mark R tests with `requires_r` from `conftest.py`.

## When a new input kind is needed

If the analysis consumes something that has no class yet (for example a
Q-matrix), add a class that fulfils `AnalysisInput`
(`core/ksplatform/inputs.py`): a `kind`, a `content_hash` and `to_payload()`.
Existing analyses are not affected.

## Package conventions to check

Before trusting a new package, run it on data with a known answer and check:

- the direction of pairs (the platform uses *(a, b) = a is a prerequisite of b*);
- whether it needs a transitively closed or reflexive relation;
- whether it matches columns by name or by position;
- how it handles missing values.

Record what you found in the script's header comment.
