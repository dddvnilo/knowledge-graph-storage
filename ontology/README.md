# Ontology and data model

The ontology is [`ks.ttl`](ks.ttl) (namespace `ks:` = `https://example.org/ks#`, a placeholder). This page explains how it is used: which named graphs exist, what goes into each, and how each kind of structure is written. The reasons for the choices are in [`../docs/decisions.md`](../docs/decisions.md).

A complete, hand-written example is [`../examples/model-example.trig`](../examples/model-example.trig). Queries answering CQ1–CQ7 on it are in [`../queries/`](../queries/), and `python tools/cq.py` checks that they still give the expected answers.

## Reused vocabularies

| Vocabulary | Used for |
|---|---|
| PROV-O (`prov:`) | provenance: every structure is a `prov:Entity`, the procedure that made it a `prov:Activity`, experts, LLMs and programs are `prov:Agent`s, prompts and methods are `prov:Plan`s |
| SKOS (`skos:`) | competencies (`ks:Competency` ⊑ `skos:Concept`), competency schemes (⊑ `skos:ConceptScheme`), mappings between schemes (`skos:exactMatch`, `closeMatch`, …) |
| OWL / RDFS | declaring classes and properties, with labels and comments; no reasoning is needed or used |

## Classes

```
prov:Entity
 ├─ ks:KnowledgeStructure        one version or run of a structure from one source
 │   ├─ ks:QMatrix
 │   ├─ ks:PrerequisiteRelation
 │   └─ ks:KnowledgeSpace
 ├─ ks:CompetencyMapping         SKOS links between two competency schemes
 └─ ks:ResponseDataset           response data, referenced only (location, checksum)
prov:Activity
 ├─ ks:ExpertElicitation
 │   └─ ks:QueryProcedure
 ├─ ks:LLMElicitation
 ├─ ks:DataDrivenDerivation      IITA, kst-transformer, …
 ├─ ks:Transformation            computed from other structures
 ├─ ks:CompetencyAlignment       produces a ks:CompetencyMapping
 └─ ks:Import                    taken over from outside, e.g. Learning Commons
ks:Test, ks:Item
ks:Competency ⊑ skos:Concept, ks:CompetencyScheme ⊑ skos:ConceptScheme
ks:QEntry, ks:CellValue (ks:Required, ks:NotRequired, ks:Unknown), ks:KnowledgeState, ks:Parameter
```

## Named graphs

Every structure `S` (and every competency mapping) occupies up to three graphs:

| Graph | Contains |
|---|---|
| `struct:S` | the **content**: the structure itself and its scope (`ks:coversItem`, `ks:coversCompetency`). The graph IRI is also the IRI of the structure. |
| `meta:S` | the **description and provenance** of `S`: its type, test, scheme, version or run, the activity, agents, plan, parameters, inputs, time |
| `closure:S` | prerequisite relations only: the **transitive closure** of the links in `struct:S`, without reflexive links |

Tests and competency schemes have one graph each, named with their own IRI (`test:T1`, `scheme:K-T1`), holding the test and its items or the scheme and its competencies.

Rules:

- **Each metadata graph is self-contained.** It describes every agent, plan and input it refers to, even if another graph already does. The same IRI always means the same thing, so the repeated triples are identical, and dropping one structure (its two or three graphs) never removes a description another structure needs.
- **Queries always name their graphs** (`GRAPH ?g`), except provenance paths, which deliberately run over all graphs (CQ4, CQ5).
- **No reasoning.** The store does not infer anything, so data states what queries need: the most specific class only (`ks:QMatrix`, not also `prov:Entity`), and `prov:wasDerivedFrom` next to `prov:wasRevisionOf`, because provenance chains follow `prov:wasDerivedFrom`.

## IRIs

| Namespace | IRI pattern | Example |
|---|---|---|
| ontology | `https://example.org/ks#{Name}` | `ks:QMatrix` |
| test | `https://example.org/data/test/{test}` | `test:T1` |
| item | `https://example.org/data/test/{test}/item/{item}` | `…/test/T1/item/z1` |
| scheme | `https://example.org/data/scheme/{scheme}` | `scheme:K-T1` |
| competency | `https://example.org/data/scheme/{scheme}/competency/{competency}` | `…/scheme/K-T1/competency/add` |
| structure (= content graph) | `https://example.org/data/structure/{id}` | `struct:qm-expert-T1-v1` |
| metadata graph | `https://example.org/data/meta/{id}` | `meta:qm-expert-T1-v1` |
| closure graph | `https://example.org/data/closure/{id}` | `closure:pr-iita-T1` |
| agent, plan, activity, input | `https://example.org/data/{agent,plan,activity,source}/{id}` | `agent:expert-01` |

Local ids match `[A-Za-z0-9][A-Za-z0-9._-]*`, so they never contain `/`. Because every level of the hierarchy is separated by `/`, two different (test, item) pairs can never produce the same IRI. Items are scoped by their test and competencies by their scheme: `z1` in T1 and `z1` in T2 are different items.

## Structures

### Q-matrix

```trig
struct:qm-expert-T1-v1 {
    struct:qm-expert-T1-v1 ks:coversItem t1:z1, t1:z2, t1:z3, t1:z4 ;
                           ks:coversCompetency k1:add, k1:reduce, k1:expand .
    t1:z2 ks:requires k1:add, k1:reduce .                          # cells with value 1
    [] a ks:QEntry ; ks:item t1:z4 ; ks:competency k1:expand ;     # unknown cell
       ks:value ks:Unknown .
    t1:z1 ks:sourceLabel "Zadatak 1" .                              # label in this source
}
```

- A cell is **1** when the content graph has `item ks:requires competency`.
- A cell is **0** when the item and the competency are both in the declared scope and there is no such triple. This is what makes true negatives countable (CQ2).
- A cell is **unknown** when a `ks:QEntry` with `ks:value ks:Unknown` exists for it. Unknown is never read as 0.
- A `ks:QEntry` is also used for a cell with a confidence or rationale. Its `ks:value` then agrees with the `ks:requires` triple.

### Prerequisite relation

```trig
struct:pr-iita-T1  { struct:pr-iita-T1 ks:coversItem t1:z1, t1:z2, t1:z3, t1:z4 .
                     t1:z1 ks:prerequisiteOf t1:z2, t1:z3 .  t1:z2 ks:prerequisiteOf t1:z4 . }
closure:pr-iita-T1 { t1:z1 ks:prerequisiteOf t1:z2, t1:z3, t1:z4 .  t1:z2 ks:prerequisiteOf t1:z4 . }
meta:pr-iita-T1    { struct:pr-iita-T1 a ks:PrerequisiteRelation ; ks:closureGraph closure:pr-iita-T1 ; … }
```

- `a ks:prerequisiteOf b` means *whoever masters b also masters a*.
- The content graph keeps the links **as the source states them** (Hasse diagram, full closure or anything between). The closure graph is computed when the relation is ingested, because Virtuoso cannot compare two closures in one query (see [infra/README.md](../infra/README.md#known-virtuoso-behaviour)).
- The same property is used between items and between competencies. The level follows from the scope (`ks:coversItem` or `ks:coversCompetency`) and from `ks:forTest` or `ks:usesScheme` in the metadata.

### Knowledge space

```trig
struct:ks-iita-T1 { struct:ks-iita-T1 ks:coversItem t1:z1, t1:z2, t1:z3, t1:z4 ;
                        ks:hasState [ a ks:KnowledgeState ] ,                            # empty state
                                    [ a ks:KnowledgeState ; ks:containsItem t1:z1 ] , … . }
```

States are listed explicitly. This is fine for small tests; a knowledge space can have exponentially many states, so for large ones it may be better to store only the relation or a basis it was computed from. That is decided when real data requires it.

### Competency mapping (Learning Commons)

```trig
struct:cm-K-T1-lc-mcm { k1:add skos:exactMatch lc:4.NF.B.3 . k1:expand skos:closeMatch lc:5.NF.A.1 . }
meta:cm-K-T1-lc-mcm   { struct:cm-K-T1-lc-mcm a ks:CompetencyMapping ;
                            ks:fromScheme scheme:K-T1 ; ks:toScheme scheme:lc-mcm ; prov:wasAttributedTo … }
```

Competencies of different schemes are never merged. A mapping is an entity with its own provenance, because who matched which competency, and how, matters for every comparison across sources. A Learning Commons framework is one more competency scheme, and its prerequisite links (`buildsTowards`) are imported as an ordinary `ks:PrerequisiteRelation` with `ks:Import` provenance. It has no special place in the model; only the queries treat it as the reference.

## Provenance

Written in the metadata graph of the structure:

```trig
struct:qm-llm-T1-r1 a ks:QMatrix ;
    ks:forTest test:T1 ; ks:usesScheme scheme:K-T1 ; ks:runLabel "r1" ;
    prov:wasGeneratedBy activity:qm-llm-T1-r1 ;
    prov:wasAttributedTo agent:llm-model-a ;
    prov:wasDerivedFrom source:T1-item-texts , source:K-T1-descriptions ;
    prov:generatedAtTime "2026-05-02T10:14:00Z"^^xsd:dateTime .

activity:qm-llm-T1-r1 a ks:LLMElicitation ;
    prov:wasAssociatedWith agent:llm-model-a ;
    prov:qualifiedAssociation [ a prov:Association ; prov:agent agent:llm-model-a ;
                                prov:hadPlan plan:prompt-qm-v1 ] ;
    prov:used source:T1-item-texts , source:K-T1-descriptions ;
    ks:hasParameter [ a ks:Parameter ; ks:parameterName "temperature" ; ks:parameterValue 0.0 ] .
```

| Question | Where |
|---|---|
| who | `prov:wasAttributedTo`, `prov:wasAssociatedWith` (an LLM or program is a `prov:SoftwareAgent` with `ks:softwareVersion`) |
| by which procedure | the class of the activity, and its plan (`prov:qualifiedAssociation` / `prov:hadPlan`, text in `ks:planText`) |
| with which settings | `ks:hasParameter` |
| from what | `prov:used` on the activity and `prov:wasDerivedFrom` on the structure (both are stated) |
| when | `prov:generatedAtTime`; left out when unknown |
| which version | `ks:versionLabel` + `prov:wasRevisionOf` for deliberate revisions; `ks:runLabel` for independent repeated runs |

## Not decided yet

- The real namespace (replace `https://example.org/` everywhere).
- Whether Learning Commons entities keep their own identifiers instead of `…/scheme/lc-mcm/competency/…` (T7, once the data is seen).
- How large knowledge spaces are stored.
- What an export for each target R/Python package must contain (T11).
