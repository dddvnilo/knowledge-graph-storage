# Infrastructure: local Virtuoso

A local Virtuoso triple store in Docker, plus `tools/kg.py`, a small command-line tool for loading data, running queries and checking that the store works. All commands below are run from the repository root unless they say `cd infra`.

## Requirements

- Docker (on Windows and macOS: Docker Desktop)
- Python 3.11+

## Start the store

```bash
cd infra
cp .env.example .env          # Windows: copy .env.example .env
# edit .env and set DBA_PASSWORD
docker compose up -d
```

| What | Where |
|---|---|
| SPARQL endpoint (read-only, public) | http://localhost:8890/sparql |
| Conductor (admin web UI, user `dba`) | http://localhost:8890/conductor |
| Database files | `infra/virtuoso-data/` (not committed) |

`DBA_PASSWORD` only takes effect when the database is first created. To change it later, or to start from an empty store, stop the container and delete `infra/virtuoso-data/`.

Stop with `docker compose down`. Data stays in `infra/virtuoso-data/`.

## Check that it works

```bash
python -m venv .venv
.venv/bin/pip install -r tools/requirements.txt      # Windows: .venv\Scripts\pip
python tools/kg.py status --wait 60    # waits until the endpoint answers
python tools/kg.py selftest            # upload, separate named graphs, comparison queries, cleanup
```

(Run `python` from the virtual environment, or activate it first.)

`kg.py` reads the password from `infra/.env`, so no extra setup is needed. Other settings can be given as environment variables (`KG_ENDPOINT`, `KG_USER`, `KG_PASSWORD`) or as options (`--endpoint`, `--user`, `--password`).

## What the store contains: `store.toml`

[`store.toml`](../store.toml) in the repository root lists every file that belongs in the store. One command empties the store and loads them all:

```bash
python tools/kg.py rebuild           # shows what would be dropped and loaded
python tools/kg.py rebuild --yes     # does it
```

All files are parsed before anything is dropped, so a file with a syntax error stops the rebuild and leaves the store as it was. Files that are not in `store.toml` are not in the store after a rebuild; this keeps the store reproducible from the repository.

| Folder | What goes there |
|---|---|
| `ontology/` | the project's ontology (`.ttl`), loaded into one named graph |
| `data/` | data as TriG, one named graph per structure, with provenance |
| `examples/` | data used only to test the infrastructure |

## Everyday use

```bash
python tools/kg.py load examples/smoke.trig            # TriG: each GRAPH block goes to its own named graph
python tools/kg.py load file.ttl --graph https://...   # single-graph formats need a target graph
python tools/kg.py load examples/smoke.trig --replace  # replace graph contents instead of adding
python tools/kg.py graphs                              # named graphs and triple counts
python tools/kg.py query "SELECT * WHERE { GRAPH ?g { ?s ?p ?o } } LIMIT 10"
python tools/kg.py query path/to/query.rq --format csv
python tools/kg.py drop --graph https://...
python tools/kg.py reset            # shows what would be deleted
python tools/kg.py reset --yes      # deletes all non-system named graphs
```

`load` is for trying things out; anything that should stay belongs in `store.toml`.

Supported input formats: `.trig`, `.nq`, `.ttl`, `.nt`, `.rdf`/`.owl` (RDF/XML), `.jsonld`.

Writes use the SPARQL 1.1 Graph Store HTTP Protocol with digest authentication, one request per named graph. A load is **not atomic**: if one graph fails to upload, the graphs before it are already written. For very large files (e.g. a full Learning Commons dump) Virtuoso's bulk loader (`ld_dir` + `rdf_loader_run`) is much faster; it is not set up yet.

## Known Virtuoso behaviour

Checked on Virtuoso 7.2.17 (the Docker image above).

**Comparing two graphs works with standard SPARQL.** Links in structure A that are not in structure B, with `MINUS` or `FILTER NOT EXISTS`:

```sparql
SELECT ?a ?b WHERE {
  GRAPH ex:structure-a { ?a ex:prerequisiteOf ?b }
  MINUS { GRAPH ex:structure-b { ?a ex:prerequisiteOf ?b } }
}
```

**Transitive paths (`p+`, `p*`) are very limited.** With the path inside `GRAPH`, Virtuoso fails with *"transitive start not given"* or *"neither end of it is bound"* in almost every form, even when the start is a constant (`<x> p+ ?o`). What works:

- a path with both ends constant, e.g. `ASK { GRAPH g { <x> p+ <y> } }`;
- the closure of **one** graph with Virtuoso's own (non-standard) syntax, the start bound by a join:

  ```sparql
  SELECT DISTINCT ?a ?b WHERE {
    GRAPH ex:structure-a { ?a ex:prerequisiteOf ?x }
    { SELECT ?a ?b WHERE { GRAPH ex:structure-a { ?a ex:prerequisiteOf ?b } } }
    OPTION (TRANSITIVE, t_distinct, t_in(?a), t_out(?b), t_min(1))
  }
  ```

Two closures in one query (closure of A `MINUS` closure of B) fail in every form tried. **Consequence for the data model:** comparisons on transitive closures (the default evaluation mode) need the closures stored in the graph, computed when a structure is ingested, so that they can be compared with plain `MINUS`. `kg.py selftest` checks each of the working forms above.

**Paths over all graphs work with standard SPARQL.** Outside a `GRAPH` clause, `<x> p+ ?o` with a constant start works, and so does `?s p+ ?d` when `?d` is bound by a join or `VALUES`. A start bound by `VALUES` does not work. The provenance queries (CQ4, CQ5 in `queries/`) use these forms.

**`BIND` cannot use the variable of an earlier `BIND`.** The result is silently empty. Write the whole expression in one `BIND` (CQ2 computes kappa this way).

**`EXISTS` used as a value gives `1` / `0`**, not `true` / `false`. Wrap it in `IF(EXISTS {…}, "…", "…")` for readable output.

**Queries without `GRAPH` see every graph.** A query with no `FROM` or `GRAPH` clause runs over the union of all graphs, including Virtuoso's own system graphs. Comparison queries should always name their graphs.

**Result size limit.** The public endpoint returns at most `VIRTUOSO_MAX_ROWS` rows (set in `.env`, default here 100000). Confirmed: the setting reaches `[SPARQL] ResultSetMaxRows` in the container's `virtuoso.ini`.

## Tested with

- Virtuoso Open Source 7.2.17 (`openlink/virtuoso-opensource-7:7.2.17`), Docker 29.8 on Windows 11, Python 3.11: `selftest` and `rebuild` pass.
