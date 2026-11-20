# Design decisions

Short records of decisions and why they were made. Newest first.

## 2026-11-20: Extension without modification (open/closed principle)

New packages and functions must be addable without editing existing code,
so that working analyses cannot be broken by adding new ones. Three
extension points, each with a small contract:

| To add | Add | Contract |
|---|---|---|
| an analysis | a module in `core/ksplatform/analyses/` + a script | module-level `ANALYSIS`, discovered automatically |
| a way to execute code (another language, an R service) | a `Runner` subclass | `run(payload) -> RunnerOutput` |
| a kind of input (Q-matrix, knowledge space) | a class | `AnalysisInput`: `kind`, `content_hash`, `to_payload()` |

Analyses declare which input kinds they accept and which output kind they
produce. The platform checks inputs before running and can chain analyses
(e.g. IITA result → `kst.space`) by kind, without knowing the packages.
How to add an analysis: `docs/adding-an-analysis.md`.

## 2026-11-20: Core is independent of the web framework

The frontend may be built in Django, which is not decided yet. Data loading,
running analyses and recording provenance live in `core/ksplatform/`, which
imports no web framework. Whatever framework is chosen calls this package.

## 2026-11-20: R packages are called through Rscript with JSON files

Each analysis is one script in `r/`, run as
`Rscript <script>.R <input.json> <output.json>`. The script always writes an
envelope with `status`, `result` or `error`, and `environment` (R and package
versions).

- Simple and easy to debug: every script can be run by hand.
- Package versions come from the script itself, so provenance is exact.
- Alternatives (rpy2, an R service with Plumber) can replace the runner later
  without touching the scripts' input and output format.

## 2026-11-20: Pair direction

`(a, b)` means *a is a prerequisite of b*, the same as `ks:prerequisiteOf` in
the group's knowledge graph. Checked by running the packages on simulated
data: DAKS and kst use the same direction, so results are not flipped.
DAKS refers to items by column index; scripts map them back to item ids.

## 2026-11-20: Everything in English

Folder names, code, comments and documentation are in English.
