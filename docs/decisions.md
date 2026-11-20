# Design decisions

Short records of decisions about the knowledge graph and why they were made. Newest first. How the model is used in practice: [ontology/README.md](../ontology/README.md).

## 2026-11-20: Data model v0.1 (task T3)

Tested on [examples/model-example.trig](../examples/model-example.trig): queries for all of CQ1–CQ7 give the hand-computed answers (`python tools/cq.py`).

**One structure version = one named graph, with metadata and closure in their own graphs.** The content graph `struct:S` holds only the structure, so it can be compared and exported as it is. Its provenance is in `meta:S`. This is what lets several versions of "the same" structure stand side by side, which is the key requirement of the project. One metadata graph per structure, instead of one shared metadata graph, means a structure can be replaced or removed by dropping its graphs, without editing a shared graph.

**Reuse PROV-O and SKOS; add only what neither has.** Provenance is entirely PROV-O (entities, activities, agents, plans, qualified association). Competencies and mappings are SKOS. The `ks:` vocabulary adds only the structure types, Q-matrix cells, knowledge states, activity subtypes and a few properties.

**Light OWL, no reasoning.** Classes and properties are declared with domains, ranges and comments, but nothing depends on inference: Virtuoso's reasoning is limited and none of the questions need it. Data therefore states what queries need explicitly (most specific class; `prov:wasDerivedFrom` next to `prov:wasRevisionOf`).

**Q-matrix: 1 as a triple, 0 as absence inside a declared scope, unknown as an explicit node.** Writing every cell as a node would make simple queries heavy; writing only 1s would make 0 and "not considered" look the same. The declared scope (`ks:coversItem`, `ks:coversCompetency`) makes 0 well-defined and true negatives countable. Unknown cells are explicit so they are never counted as 0.

**Prerequisite closures are stored, not computed in queries.** Virtuoso 7.2.17 cannot compare two transitive closures in one query. Storing the closure at ingest makes closure-based comparison (the default evaluation mode) a plain `FILTER NOT EXISTS`. The relation as stated by the source is kept as well, so Hasse-based comparison stays possible.

**Hierarchical IRIs separated by `/`.** Local ids may contain `-` and `.`, so joining them with `-` could make two different things share an IRI. Ids can never contain `/`, so `…/test/{test}/item/{item}` cannot collide. Items are scoped by their test and competencies by their scheme.

**Competencies of different schemes are never merged.** They are linked by a `ks:CompetencyMapping`, which has its own provenance. Learning Commons is one more scheme and one more imported structure; it is treated as the reference only by queries, not by the model.

**Namespace `https://example.org/` for now.** Placeholder until the real one is chosen; it appears only in prefixes and in `store.toml`.

**English names.** Classes `UpperCamelCase`, properties `lowerCamelCase`; labels carry language tags (`@en`, `@sr`).

## 2026-11-20: Store contents are reproducible from the repository (task T6)

`store.toml` lists every file in the store, and `python tools/kg.py rebuild --yes` empties the store and loads them. Anything not listed there is not in the store after a rebuild. All files are parsed before anything is dropped, so a broken file cannot leave a half-emptied store.
