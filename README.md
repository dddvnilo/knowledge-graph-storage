# Research Knowledge Graph for Knowledge Structures and Competencies
 
A shared knowledge graph for a research group working on Knowledge Space Theory (KST) and Cognitive Diagnostic Models (CDM). It stores knowledge structures (Q-matrices, prerequisite relations, knowledge spaces) from many sources. For each structure it records where the structure came from, so that versions from different sources can be compared and exported for analysis.
 
> **Status: design phase.** This document describes the project at a high level. The concrete data model, tooling and technical choices have not been decided yet.
 
---
 
## Quick orientation
 
- **What this is:** a shared data foundation for the group: a data model and the tooling to ingest, store, compare and export knowledge structures, integrated into a working platform.
- **What it stores:** items, competencies, Q-matrices, prerequisite relations and knowledge spaces. They come from experts, LLMs, data-driven methods (e.g. IITA), the QUERY procedure, and the open Learning Commons knowledge graph.
- **Key property:** provenance for every structure: who or what produced it, from which data, by which method, and when. Several versions of the "same" structure coexist and can be compared directly.
- **Not domain-specific:** the model must work for any subject domain. Concrete domains are only used to populate and demonstrate it.
- **Technologies named by the task:** OWL, SKOS, PROV-O, named graphs, Virtuoso, SPARQL. How exactly they are used is still open.
---
 
## Original task description
 
Project 6 of the Semantic Web course (in Serbian, verbatim):
 
> **Projekat 6: Istraživački graf znanja za strukture znanja i kompetencije**
>
> Ovaj projekat se bavi izgradnjom zajedničkog grafa znanja istraživačke grupe u kome se čuvaju stavke, kompetencije, Q-matrice, relacije preduslova i prostori znanja iz različitih izvora, kao što su eksperti, veliki jezički modeli, metode izvođenja struktura iz podataka i otvoreni graf znanja Learning Commons. Ključna osobina grafa je zapis porekla svake tvrdnje: ko ili šta je proizvelo određenu Q-matricu ili strukturu, iz kojih podataka, kojom metodom i kada, tako da više verzija istih struktura postoji jedna pored druge i može se direktno porediti. Studenti analiziraju literaturu iz oblasti grafova znanja u obrazovanju, modelovanja kompetencija i zapisa porekla podataka, kao i standarde semantičkog veba (OWL, SKOS, PROV-O, imenovani grafovi) i postojeći Learning Commons graf. Praktični deo uključuje modelovanje podataka za izabrani domen, preuzimanje i preslikavanje kompetencija i progresija učenja iz Learning Commons grafa, uvoz postojećih podataka grupe (ekspertskih i LLM Q-matrica, struktura iz QUERY procesa i struktura izvedenih iz podataka), postavljanje na Virtuoso, formulisanje SPARQL upita za poređenje struktura iz različitih izvora, kao i izvoz podataka u formate koje direktno koriste R i Python paketi za teoriju prostora znanja i kognitivno dijagnostičke modele. Cilj je stvaranje zajedničke, uporedive i ponovo upotrebljive osnove podataka za doktorska istraživanja grupe, od poređenja ekspertskih i LLM Q-matrica do poređenja ljudskih i mašinskih struktura preduslova.
 
English translation:
 
> **Project 6: Research knowledge graph for knowledge structures and competencies**
>
> This project builds a shared knowledge graph for the research group. It stores items, competencies, Q-matrices, prerequisite relations and knowledge spaces from different sources: experts, large language models, methods that derive structures from data, and the open Learning Commons knowledge graph. The key property of the graph is the provenance of every claim: who or what produced a given Q-matrix or structure, from which data, by which method and when, so that several versions of the same structures coexist and can be compared directly. Students review literature on knowledge graphs in education, competency modelling and data provenance, as well as Semantic Web standards (OWL, SKOS, PROV-O, named graphs) and the existing Learning Commons graph. The practical part covers data modelling for a chosen domain; retrieving and mapping competencies and learning progressions from the Learning Commons graph; importing the group's existing data (expert and LLM Q-matrices, structures from the QUERY process, and structures derived from data); deployment on Virtuoso; SPARQL queries that compare structures from different sources; and export to formats used directly by R and Python packages for Knowledge Space Theory and cognitive diagnostic models. The goal is a shared, comparable and reusable data foundation for the group's doctoral research, from comparing expert and LLM Q-matrices to comparing human and machine prerequisite structures.
 
---
 
## Key concepts
 
| Concept | Meaning |
|---|---|
| Item | a single task or question on a test |
| Competency | a skill or concept needed to solve items |
| Q-matrix | item × competency table: 1 if the item requires the competency (used by CDM) |
| Prerequisite relation | `a → b`: whoever masters b also masters a (between items or between competencies) |
| Knowledge space | the set of admissible knowledge states (KST) |
| QUERY procedure | building a knowledge structure by systematically questioning an expert |
| IITA | Inductive Item Tree Analysis: derives a prerequisite relation from response data |
| Provenance | the record of who or what produced something, from what, how and when |
 
---
 
## Goal
 
A single shared graph in which:
 
1. knowledge structures from any source and any domain are stored under one common model;
2. each structure carries its provenance;
3. structures from different sources can be compared;
4. structures can be exported to formats used by R and Python packages for KST and CDM.
---
 
## Questions the graph should answer
 
These questions drive the design. The model is adequate when every one of them can be answered by a query.
 
| # | Question |
|---|---|
| CQ1 | Which versions of the Q-matrix exist for a test, who or what produced them, when, and by which procedure? |
| CQ2 | How well do two Q-matrices for the same test agree (e.g. expert vs. LLM, different LLM models or prompts, repeated runs of the same LLM)? |
| CQ3 | Which prerequisite links does source A state that source B does not, and vice versa? |
| CQ4 | What did a structure derive from, directly or indirectly (full provenance chain)? |
| CQ5 | Which structures were derived from the same response data? |
| CQ6 | Which of the group's competencies have a counterpart in Learning Commons, and how are they related there? |
| CQ7 | Export a given structure for a given R/Python package, together with its provenance. |
 
---
 
## Evaluating and comparing structures
 
> **Working assumption (not confirmed):** a Learning Commons graph, e.g. the [Math Coherence Map](https://docs.learningcommons.org/knowledge-graph/datasets/math-coherence-map.md), serves as the **baseline** and is treated as **ground truth**. All other structures are evaluated against it. This may change, so the approaches below also cover the case with no ground truth.
 
Structures can be evaluated in three ways. They answer different questions and complement each other.
 
| Approach | Question it answers | Needs |
|---|---|---|
| **A. Against a reference** | How close is a structure to the baseline (ground truth)? | a reference structure |
| **B. Agreement between sources** | How similar are structures from different sources (expert, LLM, data-driven methods) to each other? | nothing beyond the structures |
| **C. Fit to response data** | How well does a structure explain how students actually responded? | response data for the test |
 
### A. Against a reference (baseline as ground truth)
 
Each structure is treated as a set of decisions (links or cells) and compared with the reference. This works like evaluating a binary classifier.
 
**Prerequisite relations** (sets of links `a → b`):
 
| Measure | What it measures |
|---|---|
| TP / FP / FN | links correctly found / wrongly added / missed |
| Precision, recall, F1 | how many found links are correct / how many correct links are found / balance of the two |
| Hamming distance | number of differing links (FP + FN), i.e. the size of the symmetric difference of the two link sets; normalised by the number of possible pairs `n(n−1)` to compare tests of different size |
| Jaccard similarity | shared links / all links in either structure |
| Structural Hamming Distance (SHD) | edits needed to turn one graph into the other (add, delete, reverse a link); from causal-discovery evaluation, counts a reversed link as one error instead of two |
 
The same structure can be written in different forms (only direct links / Hasse diagram, or the full transitive closure), so the measures must be computed on a common form:
 
- **on closures**: compares what each structure implies (reachability). This is the fairest default;
- **on Hasse diagrams**: compares only direct links, so it penalises redundant but correct links;
- **lenient**: links implied by the reference are not penalised, and only direct reference links count as misses.
(These are the evaluation modes used in [kst-transformer](https://github.com/dddvnilo/kst-transformer).)
 
**Q-matrices** (item × competency cells):
 
| Measure | What it measures |
|---|---|
| Cell accuracy / Hamming distance | share / number of cells that differ |
| True-positive and true-negative rate | required competencies found / non-required correctly left out |
| Over- and under-specification rate | competencies wrongly added / wrongly left out |
| Item (q-vector) recovery rate | share of items whose whole row is exactly right |
 
These are the criteria used to evaluate Q-matrix recovery in the CDM literature (e.g. in the R package [`Qval`](https://rdrr.io/cran/Qval/man/validation.html)).
 
**Knowledge spaces** (sets of states): precision, recall and symmetric difference over the sets of states, or the average distance from each state of one structure to the closest state of the other.
 
### B. Agreement between sources (no ground truth)
 
When there is no reliable reference, sources are compared with each other:
 
- **pairwise distance or similarity** using the same measures as in A (Hamming, Jaccard, F1 computed symmetrically), collected into a source × source matrix that shows which sources resemble each other;
- **chance-corrected agreement for Q-matrices**: Cohen's kappa for two sources, Fleiss' kappa or Krippendorff's alpha for several sources at once;
- **stability of one source**: agreement between repeated runs of the same LLM with the same prompt, or between different models and prompts;
- **consensus**: a structure built by majority vote across sources, with each source's distance to the consensus.
### C. Fit to response data
 
If response data exists for a test, a structure can be checked against how students actually answered, regardless of where it came from:
 
| Structure | Measures | Available in |
|---|---|---|
| Prerequisite relation | gamma index (concordant vs. discordant response pairs; positive supports the relation), violational coefficient VC (share of violations; lower is better) | R [`kst`](https://search.r-project.org/CRAN/refmans/kst/html/kvalidate.html) (`kvalidate`) |
| Knowledge structure | discrepancy index DI (average distance from each response pattern to the closest state; lower is better), distance agreement coefficient DA (DI relative to the distance to the power set, so it accounts for structure size) | R `kst`, [`kstMatrix`](https://search.r-project.org/CRAN/refmans/kstMatrix/html/kmdist.html) |
| Knowledge structure | probabilistic model fit (e.g. basic local independence model: likelihood, AIC, BIC) | R `pks` |
| Q-matrix | fit of a CDM estimated with that Q-matrix (AIC, BIC, absolute fit indices); Q-matrix validation methods that suggest corrections (GDI/PVAF, Wald, Hull, MLR-B, beta) | R `GDINA`, `Qval` |
 
This also gives a way to compare sources without ground truth: whichever structure fits the data better is the more plausible one.
 
### Comparing across levels
 
The Math Coherence Map links **Common Core standards** (`buildsTowards` = prerequisite → successor), while data-driven methods such as IITA produce links between **items**. To compare them, one side must be translated to the other's level:
 
- items → competencies through a Q-matrix, and competencies → standards through mappings;
- or the other way: an item-level relation derived from a competency-level relation and a Q-matrix (competence-based KST).
Each translation step can introduce errors of its own, so it must be recorded in provenance, and results should be read with that in mind.
 
### Practical points
 
- **Same identifiers and same competency list:** structures can only be compared cell by cell or link by link over the same items and competencies. If competency lists differ, they must be matched first.
- **Size normalisation and averaging:** report normalised measures, and state whether results are averaged per test (macro) or pooled over all pairs (micro).
- **Uncertainty:** with few tests or items, report confidence intervals (e.g. bootstrap), not only point values.
- **Where it is computed:** simple counts (TP, FP, FN, Hamming) can be computed directly with SPARQL. Statistical measures (kappa, model fit, validation methods) are computed on exported data in R or Python.
---
 
## Architecture
 
```text
 SOURCES                        INGEST                   STORAGE                USE
 expert Q-matrices ─────┐
 LLM Q-matrices ────────┤
 QUERY structures ──────┤                                                   ┌─► comparison queries
 data-driven methods ───┼─► packages ─► validation ─► shared graph  ────────┤
 (IITA, ML models, …)   │   (+ provenance)            (one place,           └─► export for R / Python
 Learning Commons ──────┘                              common model)            KST and CDM packages
 analysis results ──────┘
```
 
---
 
## Work areas
 
1. **Theory:** literature on knowledge graphs in education, competency modelling and data provenance; Semantic Web standards (OWL, SKOS, PROV-O, named graphs); the Learning Commons graph.
2. **Data model:** an ontology for items, competencies, structures and their provenance, reusing standard vocabularies where possible.
3. **Ingest:** input formats, validation, and conversion of source data into the graph with provenance.
4. **Learning Commons:** retrieving a relevant subset and mapping its competencies and progressions to the group's competencies.
5. **Storage:** deployment of the graph in a triple store (Virtuoso, as named by the task).
6. **Comparison:** SPARQL queries answering the questions above.
7. **Export:** formats for R and Python KST/CDM packages, with a check that a structure survives the round trip unchanged.
8. **Platform integration:** everything above working together inside a platform, not only as standalone scripts.
9. **Demonstration and write-up:** the system populated with real or realistic data, and the written report.
---
 
## Tasks
 
Each task defines a goal, an output and a completion criterion, but not *how* it is done. Whoever takes a task is responsible for making it concrete: choosing the approach, formats and tools, and documenting those choices.
 
| # | Task | Output | Done when | Depends on |
|---|---|---|---|---|
| T1 | Literature and standards review | draft of the theoretical part | KST/CDM, knowledge graphs in education, OWL/SKOS/PROV-O, named graphs and Learning Commons are covered | – |
| T2 | Comparison metrics | definition of how Q-matrices and prerequisite structures are compared | every pair of comparable structure types has a defined measure | – |
| T3 | Data model (ontology) | ontology + documentation | a hand-written example answers every question CQ1–CQ7 | T2 |
| T4 | Input formats and validation | input format specification per source type + validator | invalid input is rejected with a clear message | T3 |
| T5 | Ingest | tool that turns validated input into the graph, with provenance | every structure type can be ingested | T3, T4 |
| T6 | Storage | running triple store with reproducible loading | the store can be rebuilt and filled from scratch with one command | T5 |
| T7 | Learning Commons baseline | selected and mapped part of the Learning Commons graph | the baseline is in the graph and linked to the group's competencies | T3, T5 |
| T8 | Group data | expert and LLM Q-matrices, QUERY structures in the graph | all available data is ingested with provenance | T5 |
| T9 | Data-derived structures | structures from IITA, kst-transformer, etc. over response data | at least two methods over the same data are in the graph | T5 |
| T10 | Comparison queries | a query for each question CQ1–CQ6 | all queries run on ingested data | T2, T6 |
| T11 | Export | export for the target R and Python packages | a structure survives ingest → export → package unchanged | T6 |
| T12 | Platform integration | ingest, storage, comparison and export integrated into a working platform | a structure can be ingested, compared and exported through the platform, end to end | T5, T6, T10, T11 |
| T13 | Demonstration | end-to-end example on real or realistic data | answers to all questions are shown in one place, through the platform | T7–T12 |
| T14 | Write-up | the report | – | all |
 
---
 
## Definition of done
 
- A data model covering all structure types and their provenance.
- At least two sources for the same test in the graph, each with full provenance, comparable with each other.
- The Learning Commons baseline in the graph and linked to the group's competencies.
- Every question CQ1–CQ7 answered by a working query or export.
- At least one structure exported and loaded unchanged into an R and a Python package.
- Everything working together inside the platform.
- The written report.
---
 
## Out of scope
 
- Psychometric analyses (fitting CDMs, estimating knowledge spaces, etc.) are not performed by the graph itself. They run in R/Python packages or in the source methods, and only their results enter the graph.
- Developing new methods for deriving structures. Existing methods, including kst-transformer, are used only as sources.
---
 
## Open questions
 
- Which domain(s) does the group have data for?
- Which R and Python packages are the export targets?
- Are LLM Q-matrices produced over a given starting list of competencies, or does the LLM come up with the competencies itself?
- Which Learning Commons graph (e.g. the Math Coherence Map) serves as the baseline that other structures are compared against, and can it be treated as ground truth?
- Which of the evaluation approaches and measures (see *Evaluating and comparing structures*) are adopted?
- Which platform is the graph integrated into, and through what interface?
---
 
## Repository contents

| Path | What |
|---|---|
| `infra/` | local Virtuoso in Docker; setup and usage in [infra/README.md](infra/README.md) |
| `store.toml` | the list of files that make up the store; `python tools/kg.py rebuild --yes` loads them into an empty store |
| `ontology/` | the ontology [`ks.ttl`](ontology/ks.ttl) and how the data model uses named graphs: [ontology/README.md](ontology/README.md) |
| `queries/` | a SPARQL query for each question CQ1–CQ7, with expected results on the example in `queries/expected/` |
| `examples/` | [`model-example.trig`](examples/model-example.trig): hand-written example of the data model; `smoke.trig`: infrastructure test data |
| `data/` | data loaded into the store, as TriG (empty until T5) |
| `docs/decisions.md` | design decisions and why they were made |
| `tools/kg.py` | command-line tool: load RDF, list graphs, run queries, rebuild and self-test the store |
| `tools/cq.py` | runs the queries in `queries/` and checks them against the expected results |
| `tools/check_rdf.py` | checks the files in `store.toml` for rules the store does not enforce (closures, scopes) |
| `platform/` | a separate KST analysis platform (R packages called from Python); its role in this project is not settled |

---

## Related project
 
[kst-transformer](https://github.com/dddvnilo/kst-transformer): a transformer model that derives a prerequisite relation between items from response data, evaluated against IITA. It is one possible data-driven source for this graph. The graph is not designed around it.
 
